from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    PaymentMethodViewSet,
    AdCategoryViewSet,
    AdViewSet,
    TransactionViewSet,
    VerifyEmailView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    UserNotificationsView,
    NotificationDetailView,
    UpdateFCMTokenView,
    UpdateNotificationPreferencesView,
    AdminAdActionView,
    CouponViewSet,
    ResendOTPView,
    ContactMessageCreateView,
    ChangePasswordView,
)

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'payment-methods', PaymentMethodViewSet)
router.register(r'categories', AdCategoryViewSet)   # ← dynamic categories
router.register(r'ads', AdViewSet)
router.register(r'transactions', TransactionViewSet)
router.register(r'coupons', CouponViewSet, basename='coupon')

urlpatterns = [
    path('', include(router.urls)),

    # Auth / Email verification / Password reset
    path('verify-email/', VerifyEmailView.as_view(), name='verify-email'),
    path('resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password-reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),

    # Notifications
    path('update-fcm-token/', UpdateFCMTokenView.as_view(), name='update-fcm-token'),
    path('update-notification-preferences/', UpdateNotificationPreferencesView.as_view(), name='update-notification-preferences'),
    path('notifications/', UserNotificationsView.as_view(), name='user-notifications'),
    path('notifications/<int:pk>/', NotificationDetailView.as_view(), name='notification-detail'),

    # Admin actions (approve / reject & delete)
    path('ads/<str:ad_id>/action/', AdminAdActionView.as_view(), name='admin-ad-action'),

    # Contact Us
    path('contact/', ContactMessageCreateView.as_view(), name='contact-us'),
]