from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone
from datetime import timedelta


class ExpiringTokenAuthentication(TokenAuthentication):
    """
    Token authentication with expiry.
    Tokens expire after TOKEN_EXPIRY_DAYS days (default: 30).
    """
    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)

        from django.conf import settings
        expiry_days = getattr(settings, 'TOKEN_EXPIRY_DAYS', 30)

        if token.created < timezone.now() - timedelta(days=expiry_days):
            token.delete()
            raise AuthenticationFailed(
                'انتهت صلاحية الجلسة. يرجى تسجيل الدخول مرة أخرى.'
            )

        return user, token
