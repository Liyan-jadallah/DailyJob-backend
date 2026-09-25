import os
from django.conf import settings
from rest_framework import serializers
from .models import User, PaymentMethod, Ad, AdCategory, AdImage, Transaction, Notification, Coupon, Referral, ContactMessage
from .minimal_user_serializer import MinimalUserSerializer

def _resolve_media_url(file_field, request=None):
    if not file_field:
        return None
    name = getattr(file_field, 'name', str(file_field))
    if not name:
        return None
    if name.startswith('http://') or name.startswith('https://'):
        return name

    # Check if local file exists on disk (seed image committed in git)
    normalized = name.replace('\\', '/').lstrip('/')
    if normalized.startswith('media/'):
        normalized = normalized[6:]

    local_path = os.path.join(settings.MEDIA_ROOT, *normalized.split('/'))
    if os.path.exists(local_path):
        url = f"{settings.MEDIA_URL.rstrip('/')}/{normalized}"
        return request.build_absolute_uri(url) if request else url

    # Otherwise, use storage URL (Cloudinary for newly uploaded images)
    try:
        url = file_field.url
        if request and not url.startswith('http'):
            return request.build_absolute_uri(url)
        return url
    except Exception:
        return None

class AdCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AdCategory
        fields = ['id', 'key', 'label_ar', 'label_en', 'icon_name', 'order']


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    referred_by_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'first_name', 'last_name',
            'phone_number', 'role', 'referral_code', 'referred_by_code',
            'date_joined', 'device_id', 'fcm_token',
            'notifications_enabled', 'notify_all_ads',
            'preferred_governorates', 'preferred_categories',
        ]
        read_only_fields = ['id', 'date_joined', 'role', 'referral_code']

    def validate_username(self, value):
        if not value:
            raise serializers.ValidationError("اسم المستخدم مطلوب.")
        import re
        clean_val = re.sub(r'\s+', ' ', str(value)).strip()
        if len(clean_val) < 3:
            raise serializers.ValidationError("اسم المستخدم يجب أن يكون 3 أحرف على الأقل.")
        if len(clean_val) > 150:
            raise serializers.ValidationError("اسم المستخدم يجب ألا يتجاوز 150 حرفاً.")
        return clean_val

    def validate_email(self, value):
        if not value:
            raise serializers.ValidationError("البريد الإلكتروني مطلوب.")
        import re
        clean_email = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff\s]', '', str(value)).lower()
        if '@' not in clean_email or '.' not in clean_email:
            raise serializers.ValidationError("الرجاء إدخال بريد إلكتروني صحيح.")
        return clean_email

    def validate_password(self, value):
        from django.contrib.auth.password_validation import validate_password
        if not value or len(value) < 6:
            raise serializers.ValidationError("كلمة المرور يجب أن تكون 6 خانات على الأقل.")
        try:
            validate_password(value)
        except Exception as e:
            error_messages = e.messages if hasattr(e, 'messages') else [str(e)]
            raise serializers.ValidationError(" ".join(error_messages))
        return value

    def validate_phone_number(self, value):
        if value:
            arabic_digits = '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹'
            english_digits = '01234567890123456789'
            trans_table = str.maketrans(arabic_digits, english_digits)
            normalized = str(value).translate(trans_table)
            import re
            phone = re.sub(r'[\s\-\(\)]', '', normalized)
            return phone
        return value

    def get_fields(self):
        fields = super().get_fields()
        # عند التحديث (instance موجود)، نجعل البريد وكلمة المرور للقراءة فقط لمنع العبث بهما
        # تغيير كلمة المرور يتم حصراً عبر /api/change-password/
        if self.instance is not None:
            if 'email' in fields:
                fields['email'].read_only = True
            if 'password' in fields:
                fields['password'].read_only = True
        return fields

    def create(self, validated_data):
        referred_by_code = validated_data.pop('referred_by_code', None)
        raw_email = validated_data.get('email', '')
        clean_email = raw_email.strip().lower() if raw_email else ''
        user = User.objects.create_user(
            username=validated_data['username'],
            email=clean_email,
            password=validated_data['password'],
            phone_number=validated_data.get('phone_number', ''),
            device_id=validated_data.get('device_id', ''),
            fcm_token=validated_data.get('fcm_token', '')
        )
        if referred_by_code:
            referrer = User.objects.filter(referral_code=referred_by_code.strip().upper()).first()
            if referrer:
                Referral.objects.create(referrer=referrer, referred=user)
        return user

    def update(self, instance, validated_data):
        # منع تغيير البريد أو كلمة المرور أو الرتبة أو كود الإحالة نهائياً عبر مسار التعديل العام
        validated_data.pop('password', None)
        validated_data.pop('email', None)
        validated_data.pop('role', None)
        validated_data.pop('referral_code', None)
        return super().update(instance, validated_data)

class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = '__all__'

class AdImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    def get_image(self, obj):
        request = self.context.get('request')
        return _resolve_media_url(obj.image, request)

    class Meta:
        model = AdImage
        fields = ['id', 'image']

class AdSerializer(serializers.ModelSerializer):
    # تفاصيل المستخدم مختصرة
    user_details = MinimalUserSerializer(source='user', read_only=True)

    # جلب إيميل صاحب الإعلان فقط إذا كان الطلب من الأدمن أو صاحب الإعلان نفسه
    user_email = serializers.SerializerMethodField()

    # الصور الإضافية
    extra_images = AdImageSerializer(many=True, read_only=True)

    # الصورة الرئيسية للإعلان كـ absolute URL
    image = serializers.SerializerMethodField()

    # صورة الوصل من Transaction (محمية: للأدمن وصاحب الإعلان فقط)
    receipt_image = serializers.SerializerMethodField()

    def get_user_email(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if getattr(request.user, 'role', '') == 'admin' or obj.user_id == request.user.id:
                return obj.user.email
        return None

    def get_image(self, obj):
        request = self.context.get('request')
        url = _resolve_media_url(obj.image, request)
        if url:
            return url
        
        # Fallback to the first extra image if main image is not set
        first_extra = obj.extra_images.first()
        if first_extra and first_extra.image:
            return _resolve_media_url(first_extra.image, request)
            
        return None

    def validate_category(self, value):
        if value and value != 'all':
            from .models import AdCategory
            if not AdCategory.objects.filter(key=value, is_active=True).exists():
                import logging
                logging.getLogger(__name__).warning(f"Category '{value}' not found in AdCategory table")
        return value

    def validate_price(self, value):
        if value:
            arabic_digits = '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹'
            english_digits = '01234567890123456789'
            trans_table = str.maketrans(arabic_digits, english_digits)
            cleaned = str(value).translate(trans_table).strip()
            try:
                from decimal import Decimal
                return Decimal(cleaned)
            except Exception:
                raise serializers.ValidationError("السعر غير صالح.")
        return value

    def validate_contact_phone(self, value):
        import re
        if value:
            arabic_digits = '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹'
            english_digits = '01234567890123456789'
            trans_table = str.maketrans(arabic_digits, english_digits)
            normalized = str(value).translate(trans_table)
            phone = re.sub(r'[\s\-\(\)]', '', normalized)
            if not re.match(r'^\+?[0-9]{7,15}$', phone):
                raise serializers.ValidationError("رقم الهاتف غير صالح. يرجى إدخال رقم صحيح (مثال: 0791234567).")
            return phone
        return value

    def get_receipt_image(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        is_admin = getattr(request.user, 'role', '') == 'admin' or request.user.is_staff or request.user.is_superuser
        is_owner = obj.user_id == request.user.id
        if not (is_admin or is_owner):
            return None

        tx = obj.transactions.filter(receipt_image__isnull=False).exclude(receipt_image='').order_by('-submitted_at').first()
        if not tx:
            tx = obj.transactions.order_by('-submitted_at').first()
        if tx and tx.receipt_image:
            return _resolve_media_url(tx.receipt_image, request)
        return None

    class Meta:
        model = Ad
        fields = ['id', 'user', 'user_details', 'user_email', 'title', 'description', 'category', 'ad_type', 'governorate', 'price', 'contact_phone', 'contact_method', 'ad_duration', 'image', 'extra_images', 'receipt_image', 'status', 'views', 'created_at', 'approved_at', 'is_auto_approved']
        read_only_fields = ['id', 'created_at', 'approved_at', 'user', 'views', 'is_auto_approved']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        # status قابل للتعديل فقط من الأدمن
        is_admin = getattr(getattr(request, 'user', None), 'role', None) == 'admin'
        if not is_admin:
            fields['status'].read_only = True
        return fields

class TransactionSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    user_username = serializers.SerializerMethodField()
    user_phone = serializers.SerializerMethodField()
    payment_method_name = serializers.SerializerMethodField()
    coupon_code = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = '__all__'
        read_only_fields = ['id', 'submitted_at', 'status', 'user']

    def get_user_email(self, instance):
        return instance.user.email if instance.user else ''

    def get_user_username(self, instance):
        return instance.user.username if instance.user else ''

    def get_user_phone(self, instance):
        return getattr(instance.user, 'phone_number', '') or ''

    def get_payment_method_name(self, instance):
        return instance.payment_method.method_name if instance.payment_method else ''

    def get_coupon_code(self, instance):
        return instance.coupon.code if instance.coupon else ''

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        request = self.context.get('request')
        ret['receipt_image'] = _resolve_media_url(instance.receipt_image, request)
        if not ret.get('ad_title') and instance.ad:
            ret['ad_title'] = instance.ad.title
        ret['is_ad_active'] = bool(instance.ad and not getattr(instance.ad, 'is_deleted', False))
        return ret

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'user', 'title', 'message', 'ad_id', 'is_read', 'created_at']
        read_only_fields = ['id', 'created_at']

class CouponSerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()

    class Meta:
        model = Coupon
        fields = ['id', 'code', 'coupon_type', 'is_used', 'used_at', 'created_at', 'expires_at', 'is_expired']

    def get_is_expired(self, obj):
        return obj.is_expired()


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ['id', 'name', 'email', 'subject', 'message', 'is_resolved', 'created_at']
        read_only_fields = ['id', 'is_resolved', 'created_at']

    def validate_name(self, value):
        if len(value) > 150:
            raise serializers.ValidationError("الاسم يجب أن لا يتجاوز 150 حرفاً.")
        return value

    def validate_message(self, value):
        if len(value) > 5000:
            raise serializers.ValidationError("الرسالة يجب أن لا تتجاوز 5000 حرف.")
        if len(value.strip()) < 10:
            raise serializers.ValidationError("الرسالة قصيرة جداً.")
        return value
