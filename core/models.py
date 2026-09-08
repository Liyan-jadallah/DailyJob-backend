import uuid
from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail


class WelcomeCouponRecord(models.Model):
    """
    سجل دائم يحفظ كل إيميل وجهاز حصل على قسيمة ترحيبية.
    يبقى حتى لو حُذف الحساب، لمنع الاستغلال المتكرر.
    """
    email = models.EmailField(unique=True, db_index=True)
    device_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'welcome_coupon_records'

    def __str__(self):
        return f"{self.email} - {self.granted_at.date()}"

# 1. تعريف نموذج المستخدم أولاً
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(
        max_length=150,
        unique=False,
        validators=[UnicodeUsernameValidator()],
        verbose_name='username',
        help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.'
    )
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    role = models.CharField(max_length=50, choices=(('user', 'User'), ('admin', 'Admin')), default='user')
    referral_code = models.CharField(max_length=50, unique=True, blank=True, null=True)
    device_id = models.CharField(max_length=255, blank=True, null=True)
    fcm_token = models.CharField(max_length=255, blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    class Meta:
        db_table = 'users'
   
    def save(self, *args, **kwargs):
        if not self.referral_code:
            import uuid as uuid_lib
            self.referral_code = str(uuid_lib.uuid4())[:8].upper()
            while User.objects.filter(referral_code=self.referral_code).exists():
                self.referral_code = str(uuid_lib.uuid4())[:8].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username


# 2. تعريف باقي النماذج
class PaymentMethod(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    method_name = models.CharField(max_length=100)
    account_alias = models.CharField(max_length=100)
    instructions = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'payment_methods'
        ordering = ['method_name']

    def __str__(self):
        return self.method_name


class AdCategory(models.Model):
    """
    Dynamic ad categories — managed from the Django admin.
    The Flutter app fetches this list at runtime instead of hardcoding it.
    """
    key = models.CharField(max_length=50, unique=True, help_text="e.g. 'daily', 'fulltime', 'used'")
    label_ar = models.CharField(max_length=100, help_text="Arabic label shown in app/website")
    label_en = models.CharField(max_length=100, help_text="English label shown in app/website")
    icon_name = models.CharField(max_length=50, default='label', help_text="Material icon name (for reference)")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0, help_text="Display order (lower = first)")

    class Meta:
        db_table = 'ad_categories'
        ordering = ['order', 'key']

    def __str__(self):
        return f"{self.label_ar} ({self.key})"


class ActiveAdManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)

class Ad(models.Model):

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    AD_TYPE_CHOICES = (
        ('cars', 'السيارات'),
        ('real_estate', 'العقار'),
        ('rent', 'إيجار'),
        ('other', 'أخرى'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # استخدام settings.AUTH_USER_MODEL هو الأفضل للمفتاح الأجنبي (ForeignKey)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ads', db_constraint=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    category = models.CharField(max_length=100, db_index=True)
    ad_type = models.CharField(max_length=50, choices=AD_TYPE_CHOICES, blank=True, null=True, verbose_name="نوع الاعلان")
    governorate = models.CharField(max_length=100, db_index=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    contact_phone = models.CharField(max_length=15)
    contact_method = models.CharField(max_length=20, default='both', choices=(('both', 'Both'), ('call', 'Call'), ('whatsapp', 'WhatsApp')))
    ad_duration = models.CharField(max_length=20, default='1_day', choices=(('1_day', '1 Day'), ('1_week', '1 Week')))
    image = models.ImageField(upload_to='ads/images/', blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending', db_index=True)
    views = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True, help_text="وقت قبول الإعلان من الأدمن")

    objects = models.Manager()
    active = ActiveAdManager()

    class Meta:
        db_table = 'ads'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_status = self.status

    def save(self, *args, suppress_notifications=False, **kwargs):
        is_newly_active = (
            not suppress_notifications and
            self.pk is not None and
            self.__original_status != 'approved' and
            self.status == 'approved'
        )
        is_newly_rejected = (
            not suppress_notifications and
            self.pk is not None and
            self.__original_status != 'rejected' and
            self.status == 'rejected'
        )

        # تسجيل وقت القبول عند الموافقة على الإعلان
        if self.status == 'approved' and self.__original_status != 'approved':
            from django.utils import timezone as tz
            self.approved_at = tz.now()

        super().save(*args, **kwargs)
        self.__original_status = self.status

        if is_newly_active:
            # 1. إرسال إشعار شخصي لصاحب الإعلان بالقبول
            try:
                Notification.objects.create(
                    user=self.user,
                    title="✅ تم نشر إعلانك",
                    message=f"تمت الموافقة على إعلانك '{self.title}' وهو الآن متاح للجميع.",
                    ad_id=self.id
                )
            except Exception:
                pass

            # 2. إرسال إشعار عام للجميع (عبر Celery)
            try:
                from .tasks import send_global_notification_task
                send_global_notification_task.delay(self.id, self.title, self.user.id, getattr(self, 'category', ''))
            except Exception:
                pass

        if is_newly_rejected:
            # إرسال إشعار شخصي لصاحب الإعلان بالرفض
            try:
                Notification.objects.create(
                    user=self.user,
                    title="❌ تم رفض إعلانك",
                    message=f"للأسف تم رفض إعلانك '{self.title}'. يمكنك التواصل معنا لمعرفة السبب.",
                    ad_id=self.id
                )
            except Exception:
                pass

    def __str__(self):
        return self.title


class AdImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='extra_images')
    image = models.ImageField(upload_to='ads/images/')

    class Meta:
        db_table = 'ad_images'

    def __str__(self):
        return f"Image for ad {self.ad_id}"


class Coupon(models.Model):
    COUPON_TYPE_CHOICES = (
        ('free_ad', 'Free Ad'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='coupons')
    code = models.CharField(max_length=50, unique=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPE_CHOICES, default='free_ad')
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'coupons'

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=30)
        super().save(*args, **kwargs)

    def is_expired(self):
        if self.expires_at and timezone.now() > self.expires_at:
            return True
        return False

    def __str__(self):
        return f"{self.code} - {self.user.username} ({'Used' if self.is_used else 'Active'})"


class Referral(models.Model):
    referrer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals')
    referred = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referred_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'referrals'

    def __str__(self):
        return f"{self.referrer.username} invited {self.referred.username}"


class Transaction(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='transactions')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='transactions')
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    receipt_image = models.ImageField(upload_to='transactions/receipts/', blank=True, null=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transactions'

    def __str__(self):
        return f"Transaction {self.id} - Ad: {self.ad.title}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    ad_id = models.UUIDField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'

    def __str__(self):
        return f"{self.user.username} - {self.title}"


# 3. تعريف الـ Signals في النهاية (بعد أن يتعرف جانغو على كل النماذج)
# Old notification signal removed in favor of Celery task in Ad.save()


@receiver(post_save, sender=Transaction)
def notify_admins_of_transaction(sender, instance, created, **kwargs):
    if created:
        # 1. Fetch all admin users
        admin_users = User.objects.filter(role='admin') # Assuming role='admin'

        # 2. Create in-app notifications
        notifications = [
            Notification(
                user=admin,
                title="إيصال دفع جديد",
                message=f"تم استلام إيصال دفع جديد من المستخدم {instance.user.email}. الرابط: {instance.receipt_image.url if instance.receipt_image else 'No image'}"
            ) for admin in admin_users
        ]
        Notification.objects.bulk_create(notifications)

        # 3. Send email alert
        admin_emails = [admin.email for admin in admin_users if admin.email]
        if admin_emails:
            from django.core.mail import EmailMessage
            email = EmailMessage(
                subject="إيصال دفع جديد للمراجعة",
                body=f"تم استلام إيصال دفع جديد من المستخدم: {instance.user.email}.\nتجد الإيصال مرفقاً بهذه الرسالة.",
                from_email=settings.EMAIL_HOST_USER,
                to=admin_emails,
            )
            if instance.receipt_image:
                try:
                    email.attach(instance.receipt_image.name, instance.receipt_image.read(), 'image/jpeg')
                except Exception:
                    pass
            email.send(fail_silently=True)


@receiver(post_save, sender=Notification)
def send_push_on_notification_create(sender, instance, created, **kwargs):
    """
    إرسال إشعار Firebase Push للمستخدم فور حفظ إشعار جديد في قاعدة البيانات
    """
    if created:
        from .firebase_utils import send_push_notification
        try:
            unread_count = Notification.objects.filter(user=instance.user, is_read=False).count()
            send_push_notification(
                user=instance.user,
                title=instance.title,
                body=instance.message,
                data={'ad_id': str(instance.ad_id) if instance.ad_id else ''},
                badge_count=unread_count
            )
        except Exception as e:
            print(f"Error triggering push signal: {e}")


class AdView(models.Model):
    """
    سجل المشاهدات الفريدة لكل إعلان.
    يضمن احتساب المشاهدة مرة واحدة فقط لكل حساب مسجل.
    """
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE, related_name='ad_views')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='viewed_ads')
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ad_views'
        constraints = [
            models.UniqueConstraint(fields=['ad', 'user'], name='unique_ad_user_view', condition=models.Q(user__isnull=False))
        ]

    def __str__(self):
        return f"Ad {self.ad_id} viewed by {self.user or self.ip_address}"


class ContactMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150)
    email = models.EmailField()
    subject = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'contact_messages'
        ordering = ['-created_at']

    def __str__(self):
        return f"Message from {self.name} - {self.email}"


