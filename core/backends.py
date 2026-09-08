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

        # البحث بالإيميل فقط — username غير مدعوم للدخول
        user = UserModel.objects.filter(email=username).first()

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
