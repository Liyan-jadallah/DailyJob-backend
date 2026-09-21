from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model

class EmailOnlyBackend(ModelBackend):
    """
    Authentication backend that only allows login by email.
    Username may be duplicated across accounts — email is the unique identifier.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)

        # البحث بالإيميل فقط دون حساسية للأحرف الكبيرة أو الصغيرة وتنظيف المحارف الخفية
        import re
        clean_email = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff\s]', '', str(username or '')).lower()
        user = UserModel.objects.filter(email__iexact=clean_email).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
