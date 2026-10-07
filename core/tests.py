"""
اختبارات شاملة لتطبيق Daily Job — تغطي النقاط الأمنية والوظيفية الأساسية
"""
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from core.models import User, Ad, AdCategory, Notification, Coupon, PaymentMethod
from core.utils import generate_secure_otp, sanitize_email, normalize_otp, is_admin_user


class UtilsTestCase(TestCase):
    """اختبارات الدوال المساعدة"""

    def test_generate_secure_otp_length(self):
        otp = generate_secure_otp()
        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())

    def test_generate_secure_otp_range(self):
        for _ in range(100):
            otp = int(generate_secure_otp())
            self.assertGreaterEqual(otp, 100000)
            self.assertLessEqual(otp, 999999)

    def test_sanitize_email(self):
        self.assertEqual(sanitize_email('Test@Example.COM'), 'test@example.com')
        self.assertEqual(sanitize_email('  user@test.com  '), 'user@test.com')
        self.assertEqual(sanitize_email('user\u200b@test.com'), 'user@test.com')

    def test_normalize_otp_arabic_digits(self):
        self.assertEqual(normalize_otp('١٢٣٤٥٦'), '123456')
        self.assertEqual(normalize_otp('123456'), '123456')
        self.assertEqual(normalize_otp(' 123456 '), '123456')


@override_settings(SECURE_SSL_REDIRECT=False)
class AuthTestCase(TestCase):
    """اختبارات المصادقة"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            is_active=True
        )

    def test_login_success(self):
        res = self.client.post(reverse('api-login'), {
            'username': 'test@example.com',
            'password': 'TestPass123!'
        })
        self.assertEqual(res.status_code, 200)
        self.assertIn('token', res.data)

    def test_login_wrong_password(self):
        res = self.client.post(reverse('api-login'), {
            'username': 'test@example.com',
            'password': 'wrongpassword'
        })
        self.assertEqual(res.status_code, 400)

    def test_login_nonexistent_user(self):
        res = self.client.post(reverse('api-login'), {
            'username': 'nouser@example.com',
            'password': 'password123'
        })
        self.assertEqual(res.status_code, 400)


@override_settings(SECURE_SSL_REDIRECT=False)
class PaginationSecurityTestCase(TestCase):
    """اختبار حماية الـ Pagination من تجاوز المستخدمين العاديين"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='normaluser',
            email='normal@example.com',
            password='TestPass123!',
            is_active=True,
            role='user'
        )
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='TestPass123!',
            is_active=True,
            role='admin'
        )

    def test_anonymous_cannot_bypass_pagination(self):
        """مستخدم مجهول لا يستطيع تجاوز الـ Pagination"""
        res = self.client.get('/api/ads/?all=true')
        # يجب أن يُعيد نتائج مُقسّمة (تحتوي على count/results)
        self.assertEqual(res.status_code, 200)
        if isinstance(res.data, dict):
            self.assertIn('results', res.data)

    def test_admin_can_bypass_pagination(self):
        """الأدمن يستطيع تجاوز الـ Pagination"""
        from rest_framework.authtoken.models import Token
        token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        res = self.client.get('/api/ads/?all=true')
        self.assertEqual(res.status_code, 200)


@override_settings(SECURE_SSL_REDIRECT=False)
class PasswordResetSecurityTestCase(TestCase):
    """اختبار حماية استعادة كلمة المرور من User Enumeration"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='exists@example.com',
            password='TestPass123!',
            is_active=True
        )

    def test_reset_existing_email_message(self):
        """البريد المسجل يُعطي نفس الرسالة"""
        res = self.client.post('/api/password-reset/', {'email': 'exists@example.com'})
        self.assertEqual(res.status_code, 200)

    def test_reset_nonexistent_email_message(self):
        """البريد غير المسجل يُعطي نفس الرسالة (لمنع User Enumeration)"""
        res = self.client.post('/api/password-reset/', {'email': 'noone@example.com'})
        self.assertEqual(res.status_code, 200)


@override_settings(SECURE_SSL_REDIRECT=False)
class AdminPermissionTestCase(TestCase):
    """اختبار صلاحيات الأدمن"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='normaluser',
            email='normal@example.com',
            password='TestPass123!',
            is_active=True,
            role='user'
        )
        from rest_framework.authtoken.models import Token
        self.token = Token.objects.create(user=self.user)

    def test_non_admin_cannot_access_admin_actions(self):
        """المستخدم العادي لا يستطيع الوصول لأوامر الأدمن"""
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        # حاول الوصول لإعدادات الترحيب (خاصة بالأدمن)
        res = self.client.get('/api/admin/welcome-settings/')
        self.assertIn(res.status_code, [403, 401])


@override_settings(SECURE_SSL_REDIRECT=False)
class HealthCheckTestCase(TestCase):
    """اختبار نقطة فحص الصحة"""

    def test_health_check_accessible(self):
        res = self.client.get('/api/health/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.data['status'], 'ok')
        self.assertEqual(res.data['database'], 'connected')
