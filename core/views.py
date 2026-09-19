import os
import secrets
import uuid as uuid_lib

def generate_secure_otp():
    return f"{secrets.randbelow(900000) + 100000}"

import logging
logger = logging.getLogger(__name__)

from django.core.cache import cache
from rest_framework import viewsets, status, serializers, mixins
from rest_framework.decorators import action
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
            qs = User.objects.all().order_by('-date_joined')
            q = self.request.query_params.get('search', None)
            if q:
                from django.db.models import Q
                qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q) | Q(phone_number__icontains=q))
            return qs
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
            return Response({'error': '___ ______ ___________ ______ _____ ___________'}, status=status.HTTP_403_FORBIDDEN)

        # _________ __ ______ __________ ____ _________
        password = request.data.get('password')
        if not password or not user.check_password(password):
            return Response({'error': '______ __________ ______ __________. ________ _________ ______ __________ ___________ ______ ___________.'}, status=status.HTTP_400_BAD_REQUEST)

        # ______ _____ Token _________ ___ ____________ __________
        Token.objects.filter(user=user).delete()

        # __________ __________ ___________ (___________ #3)
        try:
            email_sender = getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com')
            send_mail(
                '___ ______ __________ ____ Daily Job',
                f'___________ {user.username}__\n\n___ ______ __________ ____ Daily Job _________.\n'
                f'______ __ _____ _____ __ _____ ___________ ________ ____________ ______ __________ _____: dailyjob2026@gmail.com\n\n'
                f'_______ ___ _______ ___________!\n_______ Daily Job',
                email_sender,
                [user.email],
                fail_silently=True,  # ___ ______ _________ ______ _____ ___________
            )
        except Exception:
            pass

        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # _________ __ ________ __________ ______ _______ _______ ___________ ____ _________ __ _____ serializer
        incoming_email = request.data.get('email', '').strip().lower()
        if incoming_email:
            existing_inactive = User.objects.filter(email__iexact=incoming_email, is_active=False).first()
            if existing_inactive:
                # ______ _______ _____________ ______ _______ ____________ ___________ __________ __ __________ _____ ______ ____________
                new_password = request.data.get('password')
                if new_password:
                    existing_inactive.set_password(new_password)
                    existing_inactive.save(update_fields=['password'])

                # ______ _________ OTP _________ __ ______ ____________
                otp_code = generate_secure_otp()
                cache.set(f'verify_{existing_inactive.email}', otp_code, timeout=600)
                email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
                try:
                    send_mail(
                        '_____ __________ __________ - Daily Job',
                        f'___________ {existing_inactive.username}__\n\n__________ ______ ____ ______ _______.\n\n_____ _____________: {otp_code}\n\n_______ ______ 10 ________ _____.',
                        email_sender,
                        [existing_inactive.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.warning(f"[AUTH] Inactive account OTP sending failed: {e}")
                return Response(
                    {
                        'message': '_____ ___________ _________________ ______ __________ ____ ___________ ______ _______. ___ _________ _____ __________ ________ __ ________ __________ __________ __________.',
                        'code': 'inactive_account_otp_sent',
                        'email': existing_inactive.email,
                    },
                    status=status.HTTP_200_OK
                )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 1. __________ ________ ____________ ____ _________
        otp_code = generate_secure_otp()
        cache.set(f'verify_{user.email}', otp_code, timeout=600)
        
        # 2. __________ _________ ___________ __________
        email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
        email_sent = False
        try:
            send_mail(
                '__________ __________ ____ Daily Job',
                f'___________ {user.username}__\n__________ ____________!\n\n_____ _____________ _________ ____ ___: {otp_code}\n\n_____ ________ _______ ______ 10 ________ _____.',
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
                'message': '___ _________ ___________ ___________ ________ ___________ __________ _________________ _________ _____ _____ ____________.',
                'email': user.email,
            }, status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response({
                'message': '___ _________ ___________ ___________ ____ ________ _________ _____ ____________ ______________. ________ _________ _____ __________ _________ ________.',
                'email': user.email,
                'email_failed': True,
            }, status=status.HTTP_201_CREATED, headers=headers)


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    # ____ helper _________: _________ _____ ________ ____________ ____________ ____
    @staticmethod
    def _send_new_otp(email, username):
        otp_code = generate_secure_otp()
        cache.set(f'verify_{email}', otp_code, timeout=600)
        cache.delete(f'verify_attempts_{email}')  # __________ ______ ___________
        email_sender = getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com')
        send_mail(
            '_____ _________ ________ - Daily Job',
            f'___________ {username}__\n\n___ _________ _____ _________ ________ ______ ____________ ______ _______________ _____________.\n\n_______ ___________ ___: {otp_code}\n\n_____ ________ _______ ______ 10 ________ _____.',
            email_sender,
            [email],
            fail_silently=True,
        )

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        entered_otp = request.data.get('otp')

        # _____ ________ _________ ______ ___________
        cached_otp = cache.get(f'verify_{email}')

        # ______ __ ________ _____ ____ ________ ____________
        if not cached_otp:
            return Response(
                {'error': '_____ ____________ ______ _______ ____ _______ ______________. ________ _____ _____ ________ ______ _________ _____ __________ ____________.', 'code': 'expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if str(cached_otp) == str(entered_otp):
            user = User.objects.filter(email=email).first()
            if user:
                if user.is_active:
                    # ___________ _______ __________ __ ___ _______ ____________ ___________ token ___________
                    token, _ = Token.objects.get_or_create(user=user)
                    return Response({
                        'message': '__________ _______ __________. ___ _________ _________.',
                        'token': token.key,
                        'user_id': str(user.pk),
                        'email': user.email,
                        'username': user.username,
                        'role': user.role,
                        'referral_code': user.referral_code,
                    })

                user.is_active = True  # _________ ___________
                user.save()
                
                # ______ ________ __ _________ ______ ____________ __________
                cache.delete(f'verify_{email}')
                
                # ____ _________ __ ___________ _________________ _______________ ________ __________ ____
                # __________ WelcomeCouponRecord _____ Coupon ____ Coupon __________ ___ _____________
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
                    # ______ _____ _______ _____ __________ _______ ______ ______ ______ ___________
                    WelcomeCouponRecord.objects.create(
                        email=email,
                        device_id=user.device_id if user.device_id and user.device_id.strip() else None
                    )
                    # __________ ____________
                    Notification.objects.create(
                        user=user,
                        title="____ ___________ ____ ____ Daily Job!",
                        message=f"________ {user.username}__ _______ _________! ___ ______ ________ ________ ________ _________ ______________. ________ ________________ ______ _____ ________ ___ __________!",
                    )
                
                # ____ _________ __ ____________ ______ ______________ __________ ____
                referral = Referral.objects.filter(referred=user).first()
                if referral:
                    referrer = referral.referrer
                    # _________ __ _____ __________ ____ _________ ______ ____________
                    ref_code_prefix = f"REF-{user.username[:5].upper()}-"
                    if not Coupon.objects.filter(user=referrer, coupon_type='free_ad', code__startswith=ref_code_prefix).exists():
                        reward_code = f"{ref_code_prefix}{str(uuid_lib.uuid4())[:4].upper()}"
                        Coupon.objects.create(
                            user=referrer,
                            code=reward_code,
                            coupon_type='free_ad'
                        )
                        # __________ __________ _____ _______ ___ ______________
                        Notification.objects.create(
                            user=referrer,
                            title="____ ___ _____________ ________!",
                            message=f"___ _____________ ______ ____________ _________ ____! _______ ______ ________ ________ __________ ______ _____. ______________ ____ __________ ______________.",
                        )
                
                # ____ _________ __________ ____________: _________/_____ __________ ____________ ___________ _____________ ____
                token, _ = Token.objects.get_or_create(user=user)
                return Response({
                    'message': '___ _________ ___________ _________! ___________ ____ ____',
                    'token': token.key,
                    'user_id': str(user.pk),
                    'email': user.email,
                    'username': user.username,
                    'role': user.role,
                    'referral_code': user.referral_code,
                })

        # ________ ________ _ _______ ___________
        attempts_key = f'verify_attempts_{email}'
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, timeout=600)

        max_attempts = 3
        remaining = max_attempts - attempts

        if attempts >= max_attempts:
            # __________ _______ _ _________ ________ _____ ___________ _______________
            cache.delete(f'verify_{email}')
            return Response(
                {
                    'error': '____ ____________ _______ __________ ______________ _____________ (3 ____________). ___ _________ __________ ________ _____ _____ ________ ______ _________ _____ __________ ____________.',
                    'code': 'max_attempts_exceeded',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {
                'error': f'________ ______ ________. _______ {remaining} __________ __________.',
                'code': 'wrong_otp',
                'remaining': remaining,
            },
            status=status.HTTP_400_BAD_REQUEST
        )





class ResendOTPView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response({'error': '___________ _________ ___________ _________________'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email).first()
        if not user:
            return Response({'error': '___________ _________________ ______ ______ ________'}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_active:
            return Response({'message': '___________ ______ __________! ________ _________ __________.'})

        # _________ _____ __________ ________ ____
        otp_code = generate_secure_otp()
        cache.set(f'verify_{email}', otp_code, timeout=600)

        # _________ ___________
        email_sender = getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com')
        try:
            send_mail(
                '_____ __________ __________ ___________ - Daily Job',
                f'___________ {user.username}__\n\n_____ _____________ ___________ _________ ____ ___: {otp_code}\n\n_____ ________ _______ ______ 10 ________ _____.',
                email_sender,
                [user.email],
                fail_silently=False,
            )
            return Response({'message': '___ __________ _________ _____ ____________ _____ __________ _________________.'})
        except Exception as e:
            logger.warning(f"[OTP] Resend email failed: {e}")
            return Response({'message': '___ _________ _____ _________ ________ _________.'})


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]
    
    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        if not email:
            return Response(
                {'error': '___________ _________ ___________ _________________.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()
        if not user:
            return Response(
                {'error': '___________ ______ _________.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # _________ _____ ____ ________________
        otp_code = generate_secure_otp()
        cache.set(f'reset_{email}', otp_code, timeout=600)
        if user.email and user.email.lower() != email:
            cache.set(f'reset_{user.email.lower()}', otp_code, timeout=600)
            
        email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
        try:
            send_mail(
                '__________ _________ ______ __________ - Daily Job',
                f'_____________\n____ _______ __________ _________ ______ __________.\n\n_____ _________ _________ ____ ___: {otp_code}\n\n_____ ________ _______ ______ 10 ________ _____.',
                email_sender,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.warning(f"[RESET] Password reset email failed: {e}")
            
        return Response({'message': '___ _________ _____ _________ _____ __________ _________________.'})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    # ____ helper: _________ _____ ______________ ________ ____________ ______________ ____
    @staticmethod
    def _auto_resend_reset_otp(email):
        clean_email = (email or '').strip().lower()
        otp_code = generate_secure_otp()
        cache.set(f'reset_{clean_email}', otp_code, timeout=600)
        cache.delete(f'reset_attempts_{clean_email}')
        email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
        send_mail(
            '_____ ______________ ________ - Daily Job',
            f'_____________\n\n___ _________ _____ ______________ ________ ______ ____________ ______ _______________ _____________ ____ ________ ___________ ________ __________.\n\n_______ ___________ ___: {otp_code}\n\n_____ ________ _______ ______ 10 ________ _____.',
            email_sender,
            [clean_email],
            fail_silently=True,
        )

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        entered_otp = request.data.get('otp')
        new_password = request.data.get('new_password')

        # _____ ________ _________ ___________________
        cached_otp = cache.get(f'reset_{email}')

        # ______ __ ________ _____ ____ ________ ____________
        if not cached_otp:
            return Response(
                {'error': '_____ ______________ ______ __________ ______ _______ ____ _______ ______________. ___________ _____ _____ ________.', 'code': 'expired'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if str(cached_otp) == str(entered_otp):
            user = User.objects.filter(Q(email__iexact=email) | Q(username__iexact=email)).first()
            if user:
                if not new_password or len(new_password) < 6:
                    return Response(
                        {'error': '______ __________ ______ ___ _______ 6 _________ _____ _______.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                try:
                    validate_password(new_password, user=user)
                except Exception as e:
                    error_messages = e.messages if hasattr(e, 'messages') else [str(e)]
                    return Response({'error': " ".join(error_messages)}, status=status.HTTP_400_BAD_REQUEST)

                user.set_password(new_password)
                # ___ _____ _________ ___________ ______________ __ ______ __________ ___________ _________________ _________
                if not user.is_active:
                    return Response(
                        {'error': '___ __________ ______ __________ ____ __________ ______ _______. ________ _________ __________ ______ _____ _____________ _________.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user.save(update_fields=['password'])

                # _________ ___ _____ tokens ___________ __ _____ ____ _______ _______ __ ________________ ______ __________ ______ __________
                Token.objects.filter(user=user).delete()

                # ______ ________ __________ _______________ __ _________
                cache.delete(f'reset_{email}')
                if user.email:
                    cache.delete(f'reset_{user.email.lower()}')
                cache.delete(f'reset_attempts_{email}')
                if user.email:
                    cache.delete(f'reset_attempts_{user.email.lower()}')

                return Response({'message': '___ __________ ______ __________ _________. ________ _________ __________ ________ __________ _____________.'})

        # ________ ________ __ _______ ________ _______________
        attempts_key = f'reset_attempts_{email}'
        attempts = cache.get(attempts_key, 0) + 1
        cache.set(attempts_key, attempts, timeout=600)

        max_attempts = 3
        remaining = max_attempts - attempts

        if attempts >= max_attempts:
            # __________ _______ _ _________ ________ _____ ___________ _______________
            cache.delete(f'reset_{email}')
            return Response(
                {
                    'error': '____ ____________ _______ __________ ______________ _____________ (3 ____________). ___ _________ __________ ________ _____ _____ ______________ ________.',
                    'code': 'max_attempts_exceeded',
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        return Response(
            {'error': f'________ ______ ________. _______ {remaining} __________ __________.', 'code': 'wrong_otp', 'remaining': remaining},
            status=status.HTTP_400_BAD_REQUEST
        )



class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class AdCategoryViewSet(viewsets.ReadOnlyModelViewSet):
#     Read-only endpoint: GET /api/categories/
#     Returns all active ad categories ordered by 'order' field.
#     Flutter and website fetch this dynamically instead of hardcoding.
    queryset = AdCategory.objects.filter(is_active=True)
    serializer_class = AdCategorySerializer
    permission_classes = [AllowAny]


class TransactionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
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
        # _________ __ ___ _____________ ___ ________ ___________
        ad_id = self.request.data.get('ad')
        if ad_id:
            try:
                ad = Ad.objects.get(id=ad_id)
                if ad.user != self.request.user:
                    raise serializers.ValidationError({'ad': '___ ________ _________ _________ _________ _____ ___.'})
            except Ad.DoesNotExist:
                raise serializers.ValidationError({'ad': '___________ ______ _________.'})
        serializer.save(user=self.request.user)


class CouponViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # ___________ _________ _______ ___ ________ __________ __ ______________ _________ ________ ___________

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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.is_deleted = True
        instance.deleted_at = timezone.now()
        instance.save(update_fields=['is_deleted', 'deleted_at'])
        return Response(status=status.HTTP_204_NO_CONTENT)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        user = request.user if request.user.is_authenticated else None
        
        # ___ __________ _____________ ______ _____ _____________ ___ ________ ___________ ______
        is_owner = (user and instance.user_id == user.id)
        
        if not is_owner:
            ip = get_client_ip(request)
            device_id = request.headers.get('X-Device-ID') or (getattr(user, 'device_id', None) if user else None)
            
            view_recorded = False
            if user:
                # ____________ _____________ ______ __________ _____ ____ ________ ______
                _, created = AdView.objects.get_or_create(
                    ad=instance,
                    user=user,
                    defaults={'ip_address': ip, 'device_id': device_id}
                )
                view_recorded = created
            elif ip:
                # ____________ _____________ __________ ______ ____________ _________ _____ IP
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
                Q(approved_at__lt=day_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=day_cutoff) & ~Q(status='pending'))
            ).delete()

            Ad.objects.filter(
                Q(ad_duration='1_week'),
                Q(approved_at__lt=week_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=week_cutoff) & ~Q(status='pending'))
            ).delete()
        except Exception:
            pass

    def get_queryset(self):
        # 0. Automatically delete expired ads (throttled by 60s cache lock)
        AdViewSet._cleanup_expired_ads()

        # Base query __ ordered by newest first with prefetching
        queryset = Ad.objects.select_related('user').prefetch_related('extra_images', 'transactions').filter(is_deleted=False).order_by('-created_at')

        # ____ Visibility rules ________________________________________________________________________________________________
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

        # ____ Filters __________________________________________________________________________________________________________________
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

        # ____ Full-text search (independent from category filter) __________________________
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
            raise serializers.ValidationError({'images': '___ ______ ______ ________ __ 10 ______ __________ ___________.'})
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
                        raise serializers.ValidationError({"coupon_id": "____ ___________ _________ ______________."})
            except Coupon.DoesNotExist:
                raise serializers.ValidationError({"coupon_id": "___________ ____________ ______ _________ ____ ___ ________________ __________."})
        elif receipt_image and hasattr(receipt_image, 'read'):
            payment_method_id = self.request.data.get('payment_method')
            pm = None
            if payment_method_id:
                try:
                    pm = PaymentMethod.objects.filter(id=payment_method_id, is_active=True).first()
                except Exception:
                    pass
            if not pm:
                pm = PaymentMethod.objects.filter(is_active=True).first()

            Transaction.objects.create(
                ad=ad,
                user=self.request.user,
                receipt_image=receipt_image,
                payment_method=pm,
                amount=2.00 if ad.ad_duration == '1_week' else 1.00
            )

        # 4.5 __________ _________ ___________ ______ _____ ______________
        try:
            Notification.objects.create(
                user=self.request.user,
                title="___ __________ _____ ______________",
                message=f"___ __________ __________ '{ad.title}' ___________ _____ ______ _____ ______________ _________ ______ ___________.",
                ad_id=ad.id
            )
        except Exception:
            pass
            
        # 5. _________ ________ ________ ____ _________ _________ (Non-blocking daemon thread)
        # _____ ______ ____ ________ _____ ________ (Worker Timeout)
        user_email = getattr(self.request.user, 'email', '')
        ad_title = ad.title
        coupon_code = coupon.code if coupon else None
        has_receipt = bool(receipt_image)
        # _____ ____________ _________ ____ _____ thread ________ ORM _______ thread _______
        admin_emails_list = list(User.objects.filter(role='admin').values_list('email', flat=True))
        admin_emails_list = [e for e in admin_emails_list if e]

        def _send_admin_email_async():
            try:
                from django.core.mail import send_mail
                from django.db import connection
                if admin_emails_list:
                    payment_method_str = f"_______________ ___________ (______: {coupon_code})" if coupon_code else ("____________ _____ ______ __" if has_receipt else "")
                    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
                    send_mail(
                        subject='________ ________ _____________ ______________',
                        message=f'____ _____________ {user_email} _______ ________ ________ __________ "{ad_title}" {payment_method_str}.\n________ ____________ __ _______ __________.',
                        from_email=from_email,
                        recipient_list=admin_emails_list,
                        fail_silently=True,
                    )
            except Exception:
                pass
            finally:
                # ________ _________ DB ____ thread _____ connection leaks
                from django.db import connection
                connection.close()

        threading.Thread(target=_send_admin_email_async, daemon=True).start()

    def perform_update(self, serializer):
        from .models import AdImage
        ad = serializer.save()
        
        # ___________ _____ _______ ___________ (___________ _______ ____________ ______ ___ __________ __ _________ ______________)
        # __________ ________ ___________ _________ ______ ________________
        try:
            Notification.objects.create(
                user=self.request.user,
                title="__ ___ ______ _______________",
                message=f"___ __________ __________ '{ad.title}' _________.",
                ad_id=ad.id
            )
        except Exception:
            pass

        # __________ _________ _____ _____________ ____ ___________ _________
        if getattr(self.request.user, 'role', '') != 'admin':
            try:
                admin_users = User.objects.filter(role='admin')
                notifs = [
                    Notification(
                        user=admin_user,
                        title="______ ___ _________ ________",
                        message=f"____ _____________ {self.request.user.email} ___________ ________ '{ad.title}'.",
                        ad_id=ad.id
                    )
                    for admin_user in admin_users
                ]
                if notifs:
                    Notification.objects.bulk_create(notifs)
            except Exception:
                pass
        
        # 1. __________ ______ ____ _____________ ___________ _______________
        delete_main_image_val = self.request.data.get('delete_main_image')
        should_delete_main = delete_main_image_val in ('true', 'True', True, '1', 1)

        main_image = self.request.FILES.get('image')
        if main_image:
            validate_image_file(main_image)
            ad.image = main_image
            ad.save(update_fields=['image'])
        elif should_delete_main:
            ad.image = None
            ad.save(update_fields=['image'])

        # 2. __________ ______ ______ ____________ _________ (deleted_image_ids / deleted_images)
        raw_deleted = self.request.data.getlist('deleted_image_ids') or self.request.data.getlist('deleted_images')
        if not raw_deleted:
            single = self.request.data.get('deleted_image_ids') or self.request.data.get('deleted_images')
            if single:
                raw_deleted = [single]

        deleted_ids = []
        for item in raw_deleted:
            if isinstance(item, list):
                deleted_ids.extend(item)
            elif isinstance(item, str):
                item = item.strip()
                if item.startswith('[') and item.endswith(']'):
                    import json
                    try:
                        parsed = json.loads(item)
                        if isinstance(parsed, list):
                            deleted_ids.extend(parsed)
                    except Exception:
                        pass
                elif ',' in item:
                    deleted_ids.extend(item.split(','))
                else:
                    deleted_ids.append(item)
            elif isinstance(item, int):
                deleted_ids.append(item)

        cleaned_ids = []
        for d_id in deleted_ids:
            d_str = str(d_id).strip()
            if d_str:
                cleaned_ids.append(d_str)

        if cleaned_ids:
            AdImage.objects.filter(ad=ad, id__in=cleaned_ids).delete()

        # 3. __________ ______ ____________ __________ (_____ _____ _________ ___________ ____________)
        images = self.request.FILES.getlist('images')
        if images:
            for img in images:
                validate_image_file(img)
                AdImage.objects.create(ad=ad, image=img)
                
        # __________ _____ _________ ___ ______
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

    @action(detail=True, methods=['delete', 'post'], url_path=r'images/(?P<image_id>[0-9a-fA-F-]+)')
    def delete_extra_image(self, request, pk=None, image_id=None):
        ad = self.get_object()
        if ad.user != request.user and getattr(request.user, 'role', '') != 'admin':
            return Response({'error': '_____ _______ ___________ _______ ____ ___________.'}, status=status.HTTP_403_FORBIDDEN)
        from .models import AdImage
        deleted, _ = AdImage.objects.filter(ad=ad, id=image_id).delete()
        if deleted:
            return Response({'success': True, 'message': '___ ______ ___________ _________.'}, status=status.HTTP_200_OK)
        return Response({'error': '__ _____ ___________ _____ ___________ _____________.'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete', 'post'], url_path='delete-main-image')
    def delete_main_image(self, request, pk=None):
        ad = self.get_object()
        if ad.user != request.user and getattr(request.user, 'role', '') != 'admin':
            return Response({'error': '_____ _______ ___________ _______ ____ ___________.'}, status=status.HTTP_403_FORBIDDEN)
        ad.image = None
        ad.save(update_fields=['image'])
        return Response({'success': True, 'message': '___ ______ ___________ _______________ _________.'}, status=status.HTTP_200_OK)


# ____ Admin Action View ____________________________________________________________________________________________________________________
class AdminAdActionView(APIView):
#     POST /api/ads/<ad_id>/action/
    Body: { "action": "approve" } or { "action": "reject" }

#     - approve _ sets status to 'approved' (triggers notification signals)
#     - reject  _ permanently deletes the ad and all related data
    permission_classes = [IsAuthenticated]

    def post(self, request, ad_id):
        # Only admins can use this endpoint
        if getattr(request.user, 'role', '') != 'admin':
            return Response({'error': '_____ _______ ___________ __________'}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get('action')
        if action not in ('approve', 'reject', 'delete'):
            return Response({'error': '_____________ ______ ________. ___________ approve, reject, ____ delete.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ad = Ad.objects.get(id=ad_id)
        except Ad.DoesNotExist:
            return Response({'error': '___________ ______ _________'}, status=status.HTTP_404_NOT_FOUND)

        if action == 'approve':
            ad.status = 'approved'
            ad.save()  # triggers Ad.save() signal _ sends notifications
            return Response({'status': 'approved', 'message': '___ ______ ___________ ________.'})

        elif action == 'reject':
            ad.status = 'rejected'
            ad.save()
            return Response({'status': 'rejected', 'message': '___ ______ ___________.'})

        elif action == 'delete':
            # Hard-delete the ad (cascades to AdImage, Transaction)
            ad.delete()
            return Response({'status': 'deleted', 'message': '___ ______ ___________ ____________.'})


class CustomAuthToken(ObtainAuthToken):
    throttle_classes = [OTPThrottle]
    def post(self, request, *args, **kwargs):
        login_input = request.data.get('username')  # _______ ______ username ____ _________ ______ ___ _______ ________
        password = request.data.get('password')

        if not login_input or not password:
            return Response({'error': '___________ _________ ___________ __________'}, status=status.HTTP_400_BAD_REQUEST)

        # __________ _____________ _____ _____ ____________ __________
        clean_email = (login_input or '').strip().lower()
        user = User.objects.filter(email__iexact=clean_email).first()

        if not user:
            return Response({'error': '___________ __________ ______ __________'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            # _________ ______ _____ ______ _____ ________ ____ ___________ ___ __ ________ ______ _________ _________
            cached_otp = cache.get(f'verify_{user.email}')
            if not cached_otp:
                otp_code = generate_secure_otp()
                cache.set(f'verify_{user.email}', otp_code, timeout=600)
                email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
                try:
                    send_mail(
                        '_____ __________ __________ - Daily Job',
                        f'___________ {user.username}__\n\n_____ _____________ _________ ____ ___: {otp_code}\n\n_______ ______ 10 ________.',
                        email_sender,
                        [user.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
            return Response({
                'error': '___________ ______ _______. ________ __________ __________ _________________ _________.',
                'code': 'inactive_account',
                'email': user.email
            }, status=status.HTTP_403_FORBIDDEN)

        if user.check_password(password):
            token, created = Token.objects.get_or_create(user=user)
            
            # __________ _____ FCM _____ _________ __________
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
            return Response({'error': '___________ __________ ______ __________'}, status=status.HTTP_400_BAD_REQUEST)

class UpdateFCMTokenView(APIView):
#     POST /api/update-fcm-token/
#     __________ _____ FCM ____________ _________ ___________ _______ __________ _________________
    permission_classes = [IsAuthenticated]

    def post(self, request):
        fcm_token = request.data.get('fcm_token', '').strip()
        if not fcm_token:
            return Response({'error': 'fcm_token is required'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.fcm_token = fcm_token
        request.user.save(update_fields=['fcm_token'])
        logger.info(f"FCM token updated successfully for user {request.user.email}")
        return Response({'status': 'fcm_token_updated', 'user': request.user.email})


def _parse_bool(val, default=True):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return str(val).strip().lower() in ('true', '1', 't', 'yes')


class UpdateNotificationPreferencesView(APIView):
#     POST /api/update-notification-preferences/
#     GET  /api/update-notification-preferences/
#     __________ _______ _____________ _________________ ____________ (________________ _______ __________ ___________)
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'notifications_enabled': user.notifications_enabled,
            'notify_all_ads': user.notify_all_ads,
            'preferred_governorates': user.preferred_governorates or [],
            'preferred_categories': user.preferred_categories or [],
        })

    def post(self, request):
        user = request.user
        data = request.data

        update_fields = []
        if 'notifications_enabled' in data:
            user.notifications_enabled = _parse_bool(data['notifications_enabled'], default=True)
            update_fields.append('notifications_enabled')

        if 'notify_all_ads' in data:
            user.notify_all_ads = _parse_bool(data['notify_all_ads'], default=True)
            update_fields.append('notify_all_ads')

        if 'preferred_governorates' in data:
            govs = data['preferred_governorates']
            if isinstance(govs, list):
                user.preferred_governorates = [str(g).strip() for g in govs if str(g).strip()]
                update_fields.append('preferred_governorates')

        if 'preferred_categories' in data:
            cats = data['preferred_categories']
            if isinstance(cats, list):
                user.preferred_categories = [str(c).strip() for c in cats if str(c).strip()]
                update_fields.append('preferred_categories')

        if update_fields:
            user.save(update_fields=update_fields)

        return Response({
            'status': 'preferences_updated',
            'notifications_enabled': user.notifications_enabled,
            'notify_all_ads': user.notify_all_ads,
            'preferred_governorates': user.preferred_governorates or [],
            'preferred_categories': user.preferred_categories or [],
        })


# ____ Notifications ____________________________________________________________________________________________________________________________
class UserNotificationsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # _____ ________ 30 __________ ____________ (_________ _____ ______ Celery Beat ______)
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
#     PATCH /api/notifications/<pk>/
#     Marks a specific notification as read.
#     DELETE /api/notifications/<pk>/
#     Deletes a specific notification.
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
            return Response({'error': '________ _________ ______ __________ ____________ _______________.'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        if not user.check_password(old_password):
            return Response({'error': '______ __________ ____________ ______ __________.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({'error': '______ __________ _____________ ______ ___ _______ 6 _________ _____ _______.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_password(new_password, user=user)
        except Exception as e:
            error_messages = e.messages if hasattr(e, 'messages') else [str(e)]
            return Response({'error': ' '.join(error_messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save(update_fields=['password'])

        # _________ ___ ______________ ___________ ___________ _______ ________
        Token.objects.filter(user=user).delete()
        new_token = Token.objects.create(user=user)

        # __________ ____________ ______ __________
        try:
            email_sender = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
            send_mail(
                '___ __________ ______ __________ - Daily Job',
                f'___________ {user.username},\n\n___ __________ ______ _______ __________ _________.\n\n______ __ _____ _____ __ ____ _______ _______________ ________ ____________ ______ __________ _____: dailyjob2026@gmail.com\n\n_______ Daily Job',
                email_sender,
                [user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({
            'message': '___ __________ ______ __________ _________.',
            'token': new_token.key,
        })


class ContactMessageCreateView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle] # _____________ _____ _____________ ________ _____ spam

    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            message = serializer.save()
            
            # ______________ _____ Celery Task __________ ___________ ____ ____________
            from .tasks import send_contact_email_task
            send_contact_email_task.delay(
                name=message.name,
                email=message.email,
                subject=message.subject,
                message=message.message
            )

            return Response(
                {'message': '___ _________ ___________ ___________ __________ ____________ ______.'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TestPushNotificationView(APIView):
#     GET /api/test-push/
#     POST /api/test-push/
#     ______ ______ ____________ ______________ ______________ Firebase _____________
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
        from .firebase_utils import _ensure_firebase_app
        import firebase_admin

        is_init = _ensure_firebase_app()
        total_users = User.objects.count()
        users_with_tokens = User.objects.exclude(fcm_token__isnull=True).exclude(fcm_token='').count()
        has_env_json = bool(os.getenv('FIREBASE_CREDENTIALS_JSON'))
        has_cred_path = bool(os.getenv('FIREBASE_CRED_PATH'))
        has_render_secret = os.path.exists('/etc/secrets/firebase-adminsdk.json')
        has_local_file = os.path.exists(os.path.join(settings.BASE_DIR, 'firebase-adminsdk.json'))

        user_info = None
        if request.user and request.user.is_authenticated:
            user_info = {
                'id': str(request.user.id),
                'username': request.user.username,
                'email': request.user.email,
                'has_fcm_token': bool(request.user.fcm_token),
                'fcm_token_preview': (request.user.fcm_token[:25] + '...') if request.user.fcm_token else None,
                'notifications_enabled': request.user.notifications_enabled,
                'notify_all_ads': request.user.notify_all_ads,
                'preferred_categories': request.user.preferred_categories or [],
                'preferred_governorates': request.user.preferred_governorates or [],
            }

        return Response({
            'status': 'ok',
            'firebase_initialized': is_init,
            'firebase_apps': [a.name for a in firebase_admin._apps.values()] if firebase_admin._apps else [],
            'credentials_source': {
                'env_FIREBASE_CREDENTIALS_JSON': has_env_json,
                'env_FIREBASE_CRED_PATH': has_cred_path,
                'render_secret_file': has_render_secret,
                'local_file': has_local_file,
            },
            'database_stats': {
                'total_users': total_users,
                'users_with_fcm_token': users_with_tokens,
            },
            'current_user': user_info,
        })

    def post(self, request):
        if getattr(request.user, 'role', '') != 'admin':
            return Response({'error': 'Admin access required.'}, status=status.HTTP_403_FORBIDDEN)
        from .firebase_utils import send_push_notification, send_topic_notification, send_multicast_push_notification, _ensure_firebase_app

        if not _ensure_firebase_app():
            return Response({
                'success': False,
                'error': 'Firebase Admin SDK is NOT initialized. Check FIREBASE_CREDENTIALS_JSON or firebase-adminsdk.json.',
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        title = request.data.get('title', '__ __________ __________ ________ __ Daily Job')
        body = request.data.get('body', '______ _______ _____ _____________ _______ _______ ___ ______ _________________ ______ _________ 100%!')
        extra_data = {'test': 'true', 'timestamp': str(timezone.now().timestamp())}

        # 1. _________ _____ Topic ______ ______ ___ ______
        target_topic = request.data.get('topic')
        if target_topic:
            res = send_topic_notification(topic=target_topic, title=title, body=body, data=extra_data)
            return Response({
                'success': res,
                'type': 'topic',
                'target': target_topic,
                'message': f"Topic push to '{target_topic}' sent: {res}",
            })

        # 2. _________ _____ Token _______ ___________
        target_token = request.data.get('fcm_token')
        if target_token:
            res = send_multicast_push_notification(tokens=[target_token], title=title, body=body, data=extra_data)
            return Response({
                'success': res,
                'type': 'token',
                'target_token_preview': target_token[:25] + '...',
                'message': f"Direct push to token sent: {res}",
            })

        # 3. _________ ____________ _________ __________ ___ _____ ________ _______
        target_user = None
        if request.user and request.user.is_authenticated:
            target_user = request.user
        else:
            username_or_email = request.data.get('username') or request.data.get('email')
            if username_or_email:
                target_user = User.objects.filter(username=username_or_email).first() or User.objects.filter(email=username_or_email).first()

        if target_user:
            if not target_user.fcm_token:
                return Response({
                    'success': False,
                    'error': f"User '{target_user.username}' does NOT have an FCM token registered.",
                    'user': target_user.username,
                }, status=status.HTTP_400_BAD_REQUEST)

            res = send_push_notification(user=target_user, title=title, body=body, data=extra_data)
            return Response({
                'success': res,
                'type': 'user',
                'user': target_user.username,
                'fcm_token_preview': target_user.fcm_token[:25] + '...',
                'message': f"Push notification to user '{target_user.username}' sent: {res}",
            })

        # 4. _________ ____________ _____ __________ "all" ________________
        res = send_topic_notification(topic="all", title=title, body=body, data=extra_data)
        return Response({
            'success': res,
            'type': 'default_topic_all',
            'message': f"Broadcast test push to topic 'all' sent: {res}",
        })


class AdminGrantCouponsView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if getattr(user, 'role', '') != 'admin':
            return Response({"error": "Unauthorized"}, status=403)

        target = request.data.get('target') # 'all' or 'specific'
        user_id = request.data.get('user_id') # id if specific
        count = int(request.data.get('count', 1))

        if count <= 0 or count > 50:
            return Response({"error": "Invalid count (1-50)"}, status=400)

        users_to_grant = []
        if target == 'all':
            users_to_grant = list(User.objects.filter(is_active=True))
        elif target == 'specific':
            if not user_id:
                return Response({"error": "User ID required"}, status=400)
            try:
                u = User.objects.get(id=user_id)
                users_to_grant = [u]
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=404)
        else:
            return Response({"error": "Invalid target"}, status=400)

        import uuid as uuid_lib
        from django.utils import timezone
        from datetime import timedelta
        
        coupons_to_create = []
        notifications_to_create = []
        now = timezone.now()
        expires_at = now + timedelta(days=30)
        
        for u in users_to_grant:
            for _ in range(count):
                code = f"GIFT-{u.username[:3].upper()}-{str(uuid_lib.uuid4())[:6].upper()}"
                coupons_to_create.append(Coupon(
                    user=u,
                    code=code,
                    coupon_type='free_ad',
                    expires_at=expires_at
                ))
            
            notifications_to_create.append(Notification(
                user=u,
                title="_ _____ _______ ______!",
                message=f"___ ____ ___ {count} _____ _____ __ _______. ________ ___ ______ ________!"
            ))

        Coupon.objects.bulk_create(coupons_to_create)
        Notification.objects.bulk_create(notifications_to_create)

        return Response({"message": f"Successfully granted {count} coupons to {len(users_to_grant)} users.", "users_count": len(users_to_grant)})

class AccountDeletionRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [OTPThrottle]

    def post(self, request):
        email = request.data.get('email', '').strip().lower()
        phone = request.data.get('phone', '').strip()
        reason = request.data.get('reason', '').strip()
        
        if not email:
            return Response({'error': 'البريد الإلكتروني مطلوب'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Save the request to ContactMessage
        from .models import ContactMessage
        ContactMessage.objects.create(
            name=f'طلب حذف حساب - {email}',
            email=email,
            subject='طلب حذف حساب',
            message=f'طلب حذف حساب\nالبريد: {email}\nالهاتف: {phone}\nالسبب: {reason}'
        )
        
        # Send email notification to admin
        try:
            send_mail(
                subject=f'طلب حذف حساب - {email}',
                message=f'تم استلام طلب حذف حساب:\n\nالبريد: {email}\nالهاتف: {phone}\nالسبب: {reason}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.DEFAULT_FROM_EMAIL],
                fail_silently=True
            )
        except Exception:
            pass
        
        return Response({'message': 'تم استلام طلبكم وسيتم مراجعته خلال 48 ساعة'}, status=status.HTTP_200_OK)


class HealthCheckView(APIView):
    """
    نقطة فحص صحة واستقرار السيرفر وقاعدة البيانات.
    GET /api/health/
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from django.db import connection
        db_ok = True
        try:
            connection.ensure_connection()
        except Exception:
            db_ok = False

        status_code = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response({
            'status': 'ok' if db_ok else 'degraded',
            'database': 'connected' if db_ok else 'disconnected',
            'timestamp': timezone.now().isoformat(),
            'service': 'Daily Job API',
        }, status=status_code)
