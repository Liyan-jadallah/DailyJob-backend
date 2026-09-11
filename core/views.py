import secrets
import uuid as uuid_lib

def generate_secure_otp():
    """توليد رمز OTP عشوائي وآمن تشفيرياً مكون من 6 خانات (100000-999999)"""
    return f"{secrets.randbelow(900000) + 100000}"

import logging
logger = logging.getLogger(__name__)

from django.core.cache import cache
from rest_framework import viewsets, status, serializers
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.core.mail import send_mail
from django.conf import settings
from django.shortcuts import render
from django.db.models import Q

from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from rest_framework.throttling import AnonRateThrottle
from .permissions import IsUserOwner, IsOwnerOrReadOnly
from .validators import validate_image_file
from .models import User, PaymentMethod, Ad, AdCategory, Transaction, Notification, Coupon, Referral, WelcomeCouponRecord, AdView
from .serializers import UserSerializer, PaymentMethodSerializer, AdSerializer, TransactionSerializer, AdCategorySerializer, CouponSerializer, ContactMessageSerializer


def index(request):
    return render(request, 'index.html')


class OTPThrottle(AnonRateThrottle):
    rate = '5/min'


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return User.objects.none()
        if getattr(user, 'role', '') == 'admin':
            return User.objects.all().order_by('-date_joined')
        return User.objects.filter(id=user.id)

    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        elif self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsUserOwner()]
        return [IsAuthenticated()]

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        if user != request.user:
            return Response({'error': 'لا تملك صلاحية حذف هذا الحساب'}, status=status.HTTP_403_FORBIDDEN)

        # التحقق من كلمة المرور قبل الحذف
        password = request.data.get('password')
        if not password or not user.check_password(password):
            return Response({'error': 'كلمة المرور غير صحيحة. يرجى إدخال كلمة المرور لتأكيد حذف الحساب.'}, status=status.HTTP_400_BAD_REQUEST)

        # حذف الـ Token لإنهاء كل الجلسات النشطة
        Token.objects.filter(user=user).delete()

        # إشعار بريدي بالحذف (اقتراح #3)
        try:
            email_sender = getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com')
            send_mail(
                'تم حذف حسابك في Daily Job',
                f'مرحباً {user.username}،\n\nتم حذف حسابك في Daily Job بنجاح.\n'
                f'إذا لم تكن أنت من طلب الحذف، يرجى التواصل معنا فوراً على: dailyjob2026@gmail.com\n\n'
                f'نتمنى أن نراك مجدداً!\nفريق Daily Job',
                email_sender,
                [user.email],
                fail_silently=True,  # لا نوقف الحذف إذا فشل الإيميل
            )
        except Exception:
            pass

        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # التحقق من وجود مستخدم غير مفعّل بنفس الإيميل قبل التحقق من الـ serializer
        incoming_email = request.data.get('email', '').strip().lower()
        if incoming_email:
            existing_inactive = User.objects.filter(email__iexact=incoming_email, is_active=False).first()
            if existing_inactive:
                # إذا أدخل المستخدم كلمة مرور جديدة، نحدّثها لتمكينه من الدخول بها بعد التفعيل
                new_password = request.data.get('password')
                if new_password:
                    existing_inactive.set_password(new_password)
                    existing_inactive.save(update_fields=['password'])

                # أعد إرسال OTP بدلاً من رفض التسجيل
                otp_code = generate_secure_otp()
                cache.set(f'verify_{existing_inactive.email}', otp_code, timeout=600)
                email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
                try:
                    send_mail(
                        'رمز تأكيد حسابك - Daily Job',
                        f'مرحباً {existing_inactive.username}،\n\nحسابك مسجل لكن غير مفعّل.\n\nرمز التأكيد: {otp_code}\n\nصالح لمدة 10 دقائق فقط.',
                        email_sender,
                        [existing_inactive.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.warning(f"[AUTH] Inactive account OTP sending failed: {e}")
                return Response(
                    {
                        'message': 'هذا البريد الإلكتروني مسجل مسبقاً لكن الحساب غير مفعّل. تم إرسال رمز تأكيد جديد — يرجى إدخاله لتفعيل حسابك.',
                        'code': 'inactive_account_otp_sent',
                        'email': existing_inactive.email,
                    },
                    status=status.HTTP_200_OK
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 1. إعداد الرمز وتخزينه في الكاش
        otp_code = generate_secure_otp()
        cache.set(f'verify_{user.email}', otp_code, timeout=600)
        
        # 2. محاولة إرسال الإيميل بالرمز
        email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
        email_sent = False
        try:
            send_mail(
                'تأكيد حسابك في Daily Job',
                f'مرحباً {user.username}،\nشكراً لتسجيلك!\n\nرمز التأكيد الخاص بك هو: {otp_code}\n\nهذا الرمز صالح لمدة 10 دقائق فقط.',
                email_sender,
                [user.email],
                fail_silently=False,
            )
            email_sent = True
        except Exception as e:
            logger.warning(f"[AUTH] Email sending failed: {e}")

        user.is_active = False
        user.save(update_fields=['is_active'])
        headers = self.get_success_headers(serializer.data)

        if email_sent:
            return Response({
                'message': 'تم إنشاء الحساب بنجاح، يرجى مراجعة بريدك الإلكتروني للحصول على رمز التفعيل.',
                'email': user.email,
            }, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response({
                'message': 'تم إنشاء الحساب بنجاح، لكن تعذر إرسال رمز التفعيل تلقائياً. يرجى الضغط على إعادة إرسال الرمز.',
                'email': user.email,
                'email_failed': True,
            }, status=status.HTTP_201_CREATED, headers=headers)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    # ── helper مشترك: إنشاء رمز جديد وإرساله للمستخدم ──
    @staticmethod
    def _send_new_otp(email, username):
        otp_code = generate_secure_otp()
        cache.set(f'verify_{email}', otp_code, timeout=600)
        cache.delete(f'verify_attempts_{email}')  # إعادة ضبط العداد
        email_sender = getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com')
        send_mail(
            'رمز تفعيل جديد - Daily Job',
            f'مرحباً {username}،\n\nتم إرسال رمز تفعيل جديد لأنك تجاوزت عدد المحاولات المسموحة.\n\nرمزك الجديد هو: {otp_code}\n\nهذا الرمز صالح لمدة 10 دقائق فقط.',
            email_sender,
            [email],
            fail_silently=True,
        )

    def post(self, request):
        email = request.data.get('email')
        entered_otp = request.data.get('otp')

        # جلب الرمز المخزن لهذا الإيميل
        cached_otp = cache.get(f'verify_{email}')

        # إذا لم يوجد رمز أو انتهت صلاحيته
        if not cached_otp:
            return Response(
                {'error': 'رمز التفعيل غير صالح أو منتهي الصلاحية. يرجى طلب رمز جديد عبر الضغط على إعادة الإرسال.', 'code': 'expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if str(cached_otp) == str(entered_otp):
            user = User.objects.filter(email=email).first()
            if user:
                if user.is_active:
                    # الحساب مفعّل مسبقاً — لا نعيد التفعيل ونُرجع token مباشرة
                    token, _ = Token.objects.get_or_create(user=user)
                    return Response({
                        'message': 'حسابك مفعّل بالفعل. تم تسجيل دخولك.',
                        'token': token.key,
                        'user_id': str(user.pk),
                        'email': user.email,
                        'username': user.username,
                        'role': user.role,
                        'referral_code': user.referral_code,
                    })

                user.is_active = True  # تفعيل الحساب
                user.save()
                
                # حذف الرمز من الكاش بعد التفعيل الناجح
                cache.delete(f'verify_{email}')
                
                # ── التحقق من القسيمة الترحيبية باستخدام السجل الدائم ──
                # نستخدم WelcomeCouponRecord بدل Coupon لأن Coupon يُحذف مع المستخدم
                email_already_welcomed = WelcomeCouponRecord.objects.filter(email=email).exists()
                device_already_welcomed = False
                if user.device_id and user.device_id.strip():
                    device_already_welcomed = WelcomeCouponRecord.objects.filter(
                        device_id=user.device_id
                    ).exists()

                if not email_already_welcomed and not device_already_welcomed:
                    welcome_code = f"WELCOME-{user.username[:5].upper()}-{str(uuid_lib.uuid4())[:4].upper()}"
                    Coupon.objects.create(
                        user=user,
                        code=welcome_code,
                        coupon_type='free_ad'
                    )
                    # حفظ سجل دائم لمنع إعادة المنح حتى بعد حذف الحساب
                    WelcomeCouponRecord.objects.create(
                        email=email,
                        device_id=user.device_id if user.device_id and user.device_id.strip() else None
                    )
                    # إشعار ترحيبي
                    Notification.objects.create(
                        user=user,
                        title="🎉 مرحباً بك في Daily Job!",
                        message=f"أهلاً {user.username}، نورت منصتنا! تم منحك قسيمة إعلان مجاني كهدية ترحيبية. يمكنك استخدامها لنشر أول إعلان لك مجاناً!",
                    )
                
                # ── التحقق من الإحالة ومنح المكافأة للداعي ──
                referral = Referral.objects.filter(referred=user).first()
                if referral:
                    referrer = referral.referrer
                    # التحقق من عدم تكرار منح كوبون لنفس الإحالة
                    ref_code_prefix = f"REF-{user.username[:5].upper()}-"
                    if not Coupon.objects.filter(user=referrer, coupon_type='free_ad', code__startswith=ref_code_prefix).exists():
                        reward_code = f"{ref_code_prefix}{str(uuid_lib.uuid4())[:4].upper()}"
                        Coupon.objects.create(
                            user=referrer,
                            code=reward_code,
                            coupon_type='free_ad'
                        )
                        # إشعار للداعي بأن كوده تم استخدامه
                        Notification.objects.create(
                            user=referrer,
                            title="🎁 تم استخدام كودك!",
                            message=f"تم استخدام كود الإحالة الخاص بك! لديك الآن قسيمة إعلان مجانية لمدة شهر. استخدمها قبل انتهاء صلاحيتها.",
                        )
                
                # ── تسجيل الدخول المباشر: إنشاء/جلب التوكن وإرجاع بيانات المستخدم ──
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'message': 'تم تفعيل الحساب بنجاح! مرحباً بك 🎉',
                    'token': token.key,
                    'user_id': str(user.pk),
                    'email': user.email,
                    'username': user.username,
                    'role': user.role,
                    'referral_code': user.referral_code,
                })

        # الرمز خاطئ → نزيد العداد
        attempts_key = f'verify_attempts_{email}'
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, timeout=600)

        max_attempts = 3
        remaining = max_attempts - attempts

        if attempts >= max_attempts:
            # تجاوز الحد → إبطال الرمز لمنع التخمين العشوائي
            cache.delete(f'verify_{email}')
            return Response(
                {
                    'error': 'لقد تجاوزت الحد الأقصى للمحاولات الخاطئة (3 محاولات). تم إبطال الرمز، يرجى طلب رمز جديد عبر الضغط على إعادة الإرسال.',
                    'code': 'max_attempts_exceeded',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                'error': f'الرمز غير صحيح. لديك {remaining} محاولة متبقية.',
                'code': 'wrong_otp',
                'remaining': remaining,
            },
            status=status.HTTP_400_BAD_REQUEST
        )





class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'الرجاء إدخال البريد الإلكتروني'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({'error': 'البريد الإلكتروني غير مسجل لدينا'}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_active:
            return Response({'message': 'الحساب مفعل بالفعل! يمكنك تسجيل الدخول.'})

        # توليد رمز تأكيد جديد آمن
        otp_code = generate_secure_otp()
        cache.set(f'verify_{email}', otp_code, timeout=600)

        # إرسال الإيميل
        email_sender = getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com')
        try:
            send_mail(
                'رمز تأكيد حسابك الجديد - Daily Job',
                f'مرحباً {user.username}،\n\nرمز التأكيد الجديد الخاص بك هو: {otp_code}\n\nهذا الرمز صالح لمدة 10 دقائق فقط.',
                email_sender,
                [user.email],
                fail_silently=False,
            )
            return Response({'message': 'تم إعادة إرسال رمز التفعيل إلى بريدك الإلكتروني.'})
        except Exception as e:
            logger.warning(f"[OTP] Resend email failed: {e}")
            return Response({'message': 'تم توليد رمز تفعيل جديد بنجاح.'})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]
    
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        user = User.objects.filter(email__iexact=email).first()
        
        if user:
            # توليد رمز آمن للاستعادة
            otp_code = generate_secure_otp()
            cache.set(f'reset_{user.email}', otp_code, timeout=600)
            
            email_sender = getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com')
            try:
                send_mail(
                    'إعادة تعيين كلمة المرور - Daily Job',
                    f'مرحباً،\nلقد طلبت إعادة تعيين كلمة المرور.\n\nرمز التحقق الخاص بك هو: {otp_code}\n\nهذا الرمز صالح لمدة 10 دقائق فقط.',
                    email_sender,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                logger.warning(f"[RESET] Password reset email failed: {e}")
            
        # نرجع رسالة نجاح دائماً لدواعي أمنية ولمنع الخطأ 500
        return Response({'message': 'إذا كان البريد مسجلاً لدينا، سيصلك رمز التحقق قريباً.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    # ── helper: توليد رمز استعادة جديد وإرساله تلقائياً ──
    @staticmethod
    def _auto_resend_reset_otp(email):
        otp_code = generate_secure_otp()
        cache.set(f'reset_{email}', otp_code, timeout=600)
        cache.delete(f'reset_attempts_{email}')
        email_sender = getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com')
        send_mail(
            'رمز استعادة جديد - Daily Job',
            f'مرحباً،\n\nتم إرسال رمز استعادة جديد لأنك تجاوزت عدد المحاولات المسموحة أو انتهت صلاحية الرمز السابق.\n\nرمزك الجديد هو: {otp_code}\n\nهذا الرمز صالح لمدة 10 دقائق فقط.',
            email_sender,
            [email],
            fail_silently=True,
        )

    def post(self, request):
        email = request.data.get('email')
        entered_otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        # جلب الرمز الخاص بالاستعادة
        cached_otp = cache.get(f'reset_{email}')

        # إذا لم يوجد رمز أو انتهت صلاحيته
        if not cached_otp:
            return Response(
                {'error': 'رمز استعادة كلمة المرور غير صالح أو منتهي الصلاحية. الرجاء طلب رمز جديد.', 'code': 'expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if str(cached_otp) == str(entered_otp):
            user = User.objects.filter(email=email).first()
            if user:
                if not new_password or len(new_password) < 6:
                    return Response(
                        {'error': 'كلمة المرور يجب أن تكون 6 خانات على الأقل.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                try:
                    validate_password(new_password, user=user)
                except Exception as e:
                    error_messages = e.messages if hasattr(e, 'messages') else [str(e)]
                    return Response({'error': " ".join(error_messages)}, status=status.HTTP_400_BAD_REQUEST)

                user.set_password(new_password)
                # لا يتم تفعيل الحساب تلقائياً — يجب تأكيد البريد الإلكتروني أولاً
                if not user.is_active:
                    return Response(
                        {'error': 'تم تغيير كلمة المرور لكن حسابك غير مفعّل. يرجى تفعيل حسابك عبر رمز التأكيد أولاً.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.save(update_fields=['password'])

                # إلغاء كل الـ tokens القديمة — لمنع أي جلسة نشطة من الاستمرار بعد تغيير كلمة المرور
                Token.objects.filter(user=user).delete()

                # حذف الرمز وعداد المحاولات من الكاش
                cache.delete(f'reset_{email}')
                cache.delete(f'reset_attempts_{email}')

                return Response({'message': 'تم تغيير كلمة المرور بنجاح. يرجى تسجيل الدخول بكلمة المرور الجديدة.'})

        # الرمز خاطئ — نزيد عداد المحاولات
        attempts_key = f'reset_attempts_{email}'
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, timeout=600)

        max_attempts = 3
        remaining = max_attempts - attempts

        if attempts >= max_attempts:
            # تجاوز الحد → إبطال الرمز لمنع التخمين العشوائي
            cache.delete(f'reset_{email}')
            return Response(
                {
                    'error': 'لقد تجاوزت الحد الأقصى للمحاولات الخاطئة (3 محاولات). تم إبطال الرمز، يرجى طلب رمز استعادة جديد.',
                    'code': 'max_attempts_exceeded',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {'error': f'الرمز غير صحيح. لديك {remaining} محاولة متبقية.', 'code': 'wrong_otp', 'remaining': remaining},
            status=status.HTTP_400_BAD_REQUEST
        )



class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = [AllowAny]


class AdCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only endpoint: GET /api/categories/
    Returns all active ad categories ordered by 'order' field.
    Flutter and website fetch this dynamically instead of hardcoding.
    """
    queryset = AdCategory.objects.filter(is_active=True)
    serializer_class = AdCategorySerializer
    permission_classes = [AllowAny]


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, 'role', '') == 'admin':
            return Transaction.objects.all().order_by('-submitted_at')
        return Transaction.objects.filter(user=user).order_by('-submitted_at')

    def perform_create(self, serializer):
        receipt_file = self.request.FILES.get('receipt_image')
        if receipt_file:
            validate_image_file(receipt_file)
        # التحقق من أن المستخدم هو صاحب الإعلان
        ad_id = self.request.data.get('ad')
        if ad_id:
            try:
                ad = Ad.objects.get(id=ad_id)
                if ad.user != self.request.user:
                    raise serializers.ValidationError({'ad': 'لا يمكنك إنشاء معاملة لإعلان ليس لك.'})
            except Ad.DoesNotExist:
                raise serializers.ValidationError({'ad': 'الإعلان غير موجود.'})
        serializer.save(user=self.request.user)


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # القسائم عددها قليل، لا حاجة للتصفح — والتطبيق يتوقع قائمة مباشرة

    def get_queryset(self):
        return Coupon.objects.filter(user=self.request.user).order_by('-created_at')


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


class AdViewSet(viewsets.ModelViewSet):
    queryset = Ad.objects.all()
    serializer_class = AdSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user if request.user.is_authenticated else None
        
        # لا تحتسب المشاهدة إذا كان المستخدم هو صاحب الإعلان نفسه
        is_owner = (user and instance.user_id == user.id)
        
        if not is_owner:
            ip = get_client_ip(request)
            device_id = request.headers.get('X-Device-ID') or (getattr(user, 'device_id', None) if user else None)
            
            view_recorded = False
            if user:
                # احتساب المشاهدة لمرة واحدة فقط لكل حساب مسجل
                _, created = AdView.objects.get_or_create(
                    ad=instance,
                    user=user,
                    defaults={'ip_address': ip, 'device_id': device_id}
                )
                view_recorded = created
            elif ip:
                # احتساب المشاهدة للزوار غير المسجلين بناءً على IP
                if not AdView.objects.filter(ad=instance, user__isnull=True, ip_address=ip).exists():
                    AdView.objects.create(ad=instance, ip_address=ip, device_id=device_id)
                    view_recorded = True

            if view_recorded:
                from django.db.models import F
                Ad.objects.filter(pk=instance.pk).update(views=F('views') + 1)
                instance.refresh_from_db(fields=['views'])

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @staticmethod
    def _cleanup_expired_ads():
        from django.core.cache import cache
        if cache.get('last_expired_ads_cleanup'):
            return
        cache.set('last_expired_ads_cleanup', True, timeout=60)
        try:
            from datetime import timedelta
            from django.utils import timezone as tz
            from django.db.models import Q
            now = tz.now()
            day_cutoff = now - timedelta(hours=24)
            week_cutoff = now - timedelta(days=7)

            Ad.objects.filter(
                Q(ad_duration='1_day') | Q(ad_duration__isnull=True) | Q(ad_duration=''),
                Q(approved_at__lt=day_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=day_cutoff))
            ).delete()

            Ad.objects.filter(
                Q(ad_duration='1_week'),
                Q(approved_at__lt=week_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=week_cutoff))
            ).delete()
        except Exception:
            pass

    def get_queryset(self):
        # Base query — ordered by newest first with prefetching
        queryset = Ad.objects.select_related('user').prefetch_related('extra_images', 'transactions').filter(is_deleted=False).order_by('-created_at')

        # ── Visibility rules ────────────────────────────────────────────────
        is_admin = self.request.user.is_authenticated and getattr(self.request.user, 'role', '') == 'admin'

        if self.action in ['retrieve', 'update', 'partial_update', 'destroy']:
            from django.db.models import Q
            if is_admin:
                return queryset
            if self.request.user.is_authenticated:
                return queryset.filter(Q(status='approved') | Q(user=self.request.user))
            return queryset.filter(status='approved')

        admin_all = self.request.query_params.get('admin_all') == 'true'

        if is_admin and admin_all:
            # Admin requested all ads explicitly (for admin dashboard)
            pass
        else:
            user_filter = self.request.query_params.get('user_id')
            if user_filter and self.request.user.is_authenticated and str(self.request.user.id) == user_filter:
                # User is requesting their own ads explicitly (e.g. in My Ads screen) -> show all statuses
                pass
            else:
                # Public feed, other users, or no user_filter: only show approved ads
                queryset = queryset.filter(status='approved')

            # Exclude expired ads in real time (24h for 1_day, 7 days for 1_week)
            from datetime import timedelta
            from django.utils import timezone as tz
            from django.db.models import Q
            now = tz.now()
            day_cutoff = now - timedelta(hours=24)
            week_cutoff = now - timedelta(days=7)

            valid_day = (
                (Q(ad_duration='1_day') | Q(ad_duration__isnull=True) | Q(ad_duration='')) &
                (Q(approved_at__gte=day_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__gte=day_cutoff)))
            )
            valid_week = (
                Q(ad_duration='1_week') &
                (Q(approved_at__gte=week_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__gte=week_cutoff)))
            )
            queryset = queryset.filter(valid_day | valid_week)

        # ── Filters ─────────────────────────────────────────────────────────
        status_filter = self.request.query_params.get('status')
        user_filter = self.request.query_params.get('user_id')
        category_filter = self.request.query_params.get('category')
        ad_type_filter = self.request.query_params.get('ad_type')
        governorate_filter = self.request.query_params.get('governorate')
        search_query = self.request.query_params.get('search', '').strip()

        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if user_filter:
            queryset = queryset.filter(user_id=user_filter)

        if category_filter and category_filter != 'all':
            if category_filter == 'services':
                service_subs = ['services', 'construction', 'delivery', 'cleaning', 'moving', 'plumbing', 'electrical', 'hospitality', 'caregiving']
                queryset = queryset.filter(category__in=service_subs)
            elif category_filter == 'used':
                used_subs = ['used', 'electronics', 'furniture']
                queryset = queryset.filter(category__in=used_subs)
            elif category_filter in ('rentals', 'rental'):
                queryset = queryset.filter(category__in=['rentals', 'rental'])
            else:
                queryset = queryset.filter(category=category_filter)

        if ad_type_filter and ad_type_filter != 'all':
            if ad_type_filter == 'cars':
                queryset = queryset.filter(Q(ad_type='cars') | Q(category='cars'))
            elif ad_type_filter == 'real_estate':
                queryset = queryset.filter(Q(ad_type='real_estate') | Q(category='real_estate'))
            elif ad_type_filter == 'rent':
                queryset = queryset.filter(Q(ad_type='rent') | Q(category__in=['rentals', 'rental']))
            else:
                queryset = queryset.filter(Q(ad_type=ad_type_filter) | Q(category=ad_type_filter))

        if governorate_filter and governorate_filter != 'all':
            queryset = queryset.filter(governorate=governorate_filter)

        # ── Full-text search (independent from category filter) ─────────────
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(governorate__icontains=search_query)
            )

        return queryset

    def perform_create(self, serializer):
        import threading
        from .models import AdImage, Coupon, Transaction

        # 0. Validate all uploaded images
        main_image = self.request.FILES.get('image')
        if main_image:
            validate_image_file(main_image)

        images = self.request.FILES.getlist('images')
        if len(images) > 10:
            raise serializers.ValidationError({'images': 'لا يمكن رفع أكثر من 10 صور للإعلان الواحد.'})
        for img in images:
            validate_image_file(img)

        receipt_image = self.request.FILES.get('receipt_image') or self.request.data.get('receipt_image')
        if receipt_image and hasattr(receipt_image, 'read'):
            validate_image_file(receipt_image)
        
        # 1. Save the Ad instance (status defaults to 'pending')
        ad = serializer.save(user=self.request.user)

        # 1.1 Explicitly save main_image (since image is a SerializerMethodField in AdSerializer)
        if main_image:
            ad.image = main_image
            ad.save(update_fields=['image'])

        # 1.2 Automatically set ad_type if not provided
        if not ad.ad_type:
            if ad.category == 'cars':
                ad.ad_type = 'cars'
            elif ad.category == 'real_estate':
                ad.ad_type = 'real_estate'
            elif ad.category in ('rentals', 'rental'):
                ad.ad_type = 'rent'
            else:
                ad.ad_type = 'other'
            ad.save(update_fields=['ad_type'])
        
        # 2. Save all uploaded images (multiple images support)
        for img in images:
            AdImage.objects.create(ad=ad, image=img)
        
        # 3. Extract receipt_image and coupon_id from request data
        coupon_id = self.request.data.get('coupon_id')
        
        # 4. Create a Transaction linked to the Ad and user (using either coupon or receipt)
        coupon = None
        if coupon_id:
            from django.db import transaction
            try:
                with transaction.atomic():
                    coupon = Coupon.objects.select_for_update().get(id=coupon_id, user=self.request.user, is_used=False)
                    if not coupon.is_expired():
                        coupon.is_used = True
                        coupon.used_at = timezone.now()
                        coupon.save(update_fields=['is_used', 'used_at'])
                        
                        Transaction.objects.create(
                            ad=ad,
                            user=self.request.user,
                            coupon=coupon,
                            amount=0.00,
                            status='approved'
                        )
                    else:
                        raise serializers.ValidationError({"coupon_id": "هذه القسيمة منتهية الصلاحية."})
            except Coupon.DoesNotExist:
                raise serializers.ValidationError({"coupon_id": "القسيمة المحددة غير صالحة أو تم استخدامها مسبقاً."})
        elif receipt_image and hasattr(receipt_image, 'read'):
            Transaction.objects.create(
                ad=ad,
                user=self.request.user,
                receipt_image=receipt_image,
                amount=2.00 if ad.ad_duration == '1_week' else 1.00
            )

        # 4.5 إشعار لصاحب الإعلان بأنه قيد المراجعة
        try:
            Notification.objects.create(
                user=self.request.user,
                title="⏳ إعلانك قيد المراجعة",
                message=f"تم استلام إعلانك '{ad.title}' بنجاح، وهو الآن قيد المراجعة وسيتم نشره قريباً.",
                ad_id=ad.id
            )
        except Exception:
            pass
            
        # 5. إرسال إيميل للأدمن في خلفية النظام (Non-blocking daemon thread)
        # لمنع بطء أو تعليق طلب النشر (Worker Timeout)
        user_email = getattr(self.request.user, 'email', '')
        ad_title = ad.title
        coupon_code = coupon.code if coupon else None
        has_receipt = bool(receipt_image)
        # جلب إيميلات الأدمن قبل الـ thread لتجنب ORM داخل thread منفصل
        admin_emails_list = list(User.objects.filter(role='admin').values_list('email', flat=True))
        admin_emails_list = [e for e in admin_emails_list if e]

        def _send_admin_email_async():
            try:
                from django.core.mail import send_mail
                from django.db import connection
                if admin_emails_list:
                    payment_method_str = f"باستخدام القسيمة (كود: {coupon_code})" if coupon_code else ("بواسطة وصل الدفع" if has_receipt else "")
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
                    send_mail(
                        subject='إعلان جديد بانتظار المراجعة',
                        message=f'قام المستخدم {user_email} بنشر إعلان جديد بعنوان "{ad_title}" {payment_method_str}.\nيرجى مراجعته من لوحة التحكم.',
                        from_email=from_email,
                        recipient_list=admin_emails_list,
                        fail_silently=True,
                    )
            except Exception:
                pass
            finally:
                # إغلاق اتصال DB للـ thread لمنع connection leaks
                from django.db import connection
                connection.close()

        threading.Thread(target=_send_admin_email_async, daemon=True).start()

    def perform_update(self, serializer):
        from .models import AdImage
        ad = serializer.save()
        
        # الحفاظ على حالة الإعلان (المعتمد يبقى معتمداً حتى لا يختفي من الموقع والتطبيق)
        # إشعار صاحب الإعلان بنجاح حفظ التعديلات
        try:
            Notification.objects.create(
                user=self.request.user,
                title="✅ تم حفظ تعديلاتك",
                message=f"تم تحديث إعلانك '{ad.title}' بنجاح.",
                ad_id=ad.id
            )
        except Exception:
            pass

        # إشعار الأدمن بأن المستخدم قام بتعديل إعلانه
        if getattr(self.request.user, 'role', '') != 'admin':
            try:
                admin_users = User.objects.filter(role='admin')
                notifs = [
                    Notification(
                        user=admin_user,
                        title="✏️ تم تعديل إعلان",
                        message=f"قام المستخدم {self.request.user.email} بتعديل إعلان '{ad.title}'.",
                        ad_id=ad.id
                    )
                    for admin_user in admin_users
                ]
                if notifs:
                    Notification.objects.bulk_create(notifs)
            except Exception:
                pass
        
        # التحقق من سلامة الصورة الرئيسية وتحديثها
        main_image = self.request.FILES.get('image')
        if main_image:
            validate_image_file(main_image)
            ad.image = main_image
            ad.save(update_fields=['image'])

        # تحديث الصور الإضافية إذا قام المستخدم برفع صور جديدة
        images = self.request.FILES.getlist('images')
        if images:
            for img in images:
                validate_image_file(img)
            # حذف الصور القديمة
            AdImage.objects.filter(ad=ad).delete()
            # إضافة الصور الجديدة
            for img in images:
                AdImage.objects.create(ad=ad, image=img)
                
        # تحديث وصل الدفع إن وجد
        receipt_image = self.request.FILES.get('receipt_image') or self.request.data.get('receipt_image')
        if receipt_image:
            if hasattr(receipt_image, 'read'):
                validate_image_file(receipt_image)
            from .models import Transaction
            Transaction.objects.create(
                ad=ad,
                user=self.request.user,
                receipt_image=receipt_image
            )


# ── Admin Action View ──────────────────────────────────────────────────────────
class AdminAdActionView(APIView):
    """
    POST /api/ads/<ad_id>/action/
    Body: { "action": "approve" } or { "action": "reject" }

    - approve → sets status to 'approved' (triggers notification signals)
    - reject  → permanently deletes the ad and all related data
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ad_id):
        # Only admins can use this endpoint
        if getattr(request.user, 'role', '') != 'admin':
            return Response({'error': 'ليس لديك صلاحية الوصول'}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get('action')
        if action not in ('approve', 'reject', 'delete'):
            return Response({'error': 'الإجراء غير صحيح. استخدم approve, reject, أو delete.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ad = Ad.objects.get(id=ad_id)
        except Ad.DoesNotExist:
            return Response({'error': 'الإعلان غير موجود'}, status=status.HTTP_404_NOT_FOUND)

        if action == 'approve':
            ad.status = 'approved'
            ad.save()  # triggers Ad.save() signal → sends notifications
            return Response({'status': 'approved', 'message': 'تم قبول الإعلان ونشره.'})

        elif action == 'reject':
            ad.status = 'rejected'
            ad.save()
            return Response({'status': 'rejected', 'message': 'تم رفض الإعلان.'})

        elif action == 'delete':
            # Hard-delete the ad (cascades to AdImage, Transaction)
            ad.delete()
            return Response({'status': 'deleted', 'message': 'تم حذف الإعلان نهائياً.'})


class CustomAuthToken(ObtainAuthToken):
    throttle_classes = [OTPThrottle]
    def post(self, request, *args, **kwargs):
        login_input = request.data.get('username')  # الحقل اسمه username لكن القيمة يجب أن تكون إيميل
        password = request.data.get('password')

        if not login_input or not password:
            return Response({'error': 'الرجاء إدخال بيانات الدخول'}, status=status.HTTP_400_BAD_REQUEST)

        # الدخول بالإيميل فقط دون حساسية للأحرف
        clean_email = (login_input or '').strip().lower()
        user = User.objects.filter(email__iexact=clean_email).first()

        if not user:
            return Response({'error': 'بيانات الدخول غير صحيحة'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            # التحقق إذا كان هناك رمز ساري في الكاش، إن لم يوجد ننشئ رمزاً ونرسله
            cached_otp = cache.get(f'verify_{user.email}')
            if not cached_otp:
                otp_code = generate_secure_otp()
                cache.set(f'verify_{user.email}', otp_code, timeout=600)
                email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
                try:
                    send_mail(
                        'رمز تأكيد حسابك - Daily Job',
                        f'مرحباً {user.username}،\n\nرمز التأكيد الخاص بك هو: {otp_code}\n\nصالح لمدة 10 دقائق.',
                        email_sender,
                        [user.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            return Response({
                'error': 'الحساب غير مفعّل. يرجى تأكيد بريدك الإلكتروني أولاً.',
                'code': 'inactive_account',
                'email': user.email
            }, status=status.HTTP_403_FORBIDDEN)

        if user.check_password(password):
            token, created = Token.objects.get_or_create(user=user)
            
            # تحديث رمز FCM عند تسجيل الدخول
            fcm_token = request.data.get('fcm_token')
            if fcm_token:
                user.fcm_token = fcm_token
                user.save(update_fields=['fcm_token'])

            return Response({
                'token': token.key,
                'user_id': str(user.pk),
                'email': user.email,
                'username': user.username,
                'role': user.role,
                'referral_code': user.referral_code
            })
        else:
            return Response({'error': 'بيانات الدخول غير صحيحة'}, status=status.HTTP_400_BAD_REQUEST)



# ── Notifications ──────────────────────────────────────────────────────────────
class UserNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # جلب أحدث 30 إشعار للمستخدم (الحذف يتم عبر Celery Beat الآن)
        notifications = Notification.objects.filter(
            user=request.user
        ).order_by('-created_at')[:30]

        data = [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "ad_id": str(n.ad_id) if n.ad_id else None,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            } for n in notifications
        ]
        return Response(data)

    def patch(self, request):
        """تحديث حالة قراءة الإشعارات (إشعار محدد أو الكل)"""
        mark_all = request.data.get('mark_all', False)
        notif_id = request.data.get('id')

        if mark_all:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
            return Response({'status': 'all_marked_read'})

        if notif_id:
            updated = Notification.objects.filter(id=notif_id, user=request.user).update(is_read=True)
            if updated:
                return Response({'status': 'marked_read'})
            return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

        return Response({'error': 'Provide mark_all=true or an id'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """حذف مجموعة من الإشعارات المحددة أو حذف كل الإشعارات"""
        delete_all = request.data.get('delete_all', False)
        ids = request.data.get('ids', [])
        if delete_all or ids == 'all':
            Notification.objects.filter(user=request.user).delete()
            return Response({'status': 'all_deleted'})
        if ids:
            try:
                int_ids = [int(i) for i in ids]
            except ValueError:
                return Response({'error': 'Invalid notification IDs'}, status=status.HTTP_400_BAD_REQUEST)
            Notification.objects.filter(id__in=int_ids, user=request.user).delete()
            return Response({'status': 'deleted'})
        return Response({'error': 'No ids or delete_all provided'}, status=status.HTTP_400_BAD_REQUEST)


class NotificationDetailView(APIView):
    """
    PATCH /api/notifications/<pk>/
    Marks a specific notification as read.
    DELETE /api/notifications/<pk>/
    Deletes a specific notification.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        updated = Notification.objects.filter(id=pk, user=request.user).update(is_read=True)
        if updated:
            return Response({'status': 'marked_read'})
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        deleted, _ = Notification.objects.filter(id=pk, user=request.user).delete()
        if deleted:
            return Response({'status': 'deleted'})
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response({'error': 'يرجى إدخال كلمة المرور الحالية والجديدة.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        if not user.check_password(old_password):
            return Response({'error': 'كلمة المرور الحالية غير صحيحة.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({'error': 'كلمة المرور الجديدة يجب أن تكون 6 خانات على الأقل.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user=user)
        except Exception as e:
            error_messages = e.messages if hasattr(e, 'messages') else [str(e)]
            return Response({'error': ' '.join(error_messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=['password'])

        # إلغاء كل التوكنات القديمة وإنشاء توكن جديد
        Token.objects.filter(user=user).delete()
        new_token = Token.objects.create(user=user)

        # إشعار بتغيير كلمة المرور
        try:
            email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
            send_mail(
                'تم تغيير كلمة المرور - Daily Job',
                f'مرحباً {user.username},\n\nتم تغيير كلمة مرور حسابك بنجاح.\n\nإذا لم تكن أنت من قام بهذا التغيير، يرجى التواصل معنا فوراً على: dailyjob2026@gmail.com\n\nفريق Daily Job',
                email_sender,
                [user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({
            'message': 'تم تغيير كلمة المرور بنجاح.',
            'token': new_token.key,
        })


class ContactMessageCreateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle] # استخدام نفس التحديد لتجنب الـ spam

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save()
            
            # استدعاء الـ Celery Task لإرسال الإيميل في الخلفية
            from .tasks import send_contact_email_task
            send_contact_email_task.delay(
                name=message.name,
                email=message.email,
                subject=message.subject,
                message=message.message
            )

            return Response(
                {'message': 'تم إرسال رسالتك بنجاح، شكراً لتواصلك معنا.'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

