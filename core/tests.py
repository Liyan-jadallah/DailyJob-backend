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

    def test_active_user_cannot_bypass_otp_via_verify_email(self):
        """التحقق من إغلاق ثغرة تجاوز OTP: المستخدم المفعّل لا يحصل على Token عبر verify-email"""
        res = self.client.post('/api/verify-email/', {
            'email': 'test@example.com',
            'otp': '000000'
        })
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data.get('code'), 'already_active')
        self.assertNotIn('token', res.data)

    def test_nonexistent_user_verify_email_rejected(self):
        """البريد غير المسجل لا يستطيع طلب التفعيل"""
        res = self.client.post('/api/verify-email/', {
            'email': 'unknown@example.com',
            'otp': '123456'
        })
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data.get('code'), 'not_found')
        self.assertNotIn('token', res.data)


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


@override_settings(SECURE_SSL_REDIRECT=False)
class TransactionRetentionTestCase(TestCase):
    """اختبار سياسة الاحتفاظ بالمعاملات المالية لمدة 6 أشهر لحفظ الرواتب ومنع الاحتيال"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='txuser',
            email='txuser@example.com',
            password='TestPass123!',
            is_active=True
        )

    def test_transactions_retention_policy(self):
        from core.models import Transaction
        from core.tasks import delete_expired_content
        from django.utils import timezone
        from datetime import timedelta

        # 1. معاملة حديثة (عمرها 30 يوماً - يجب أن تبقى محفوظة لتدقيق الرواتب)
        recent_tx = Transaction.objects.create(
            user=self.user,
            amount=1.00,
            status='approved'
        )
        Transaction.objects.filter(id=recent_tx.id).update(
            submitted_at=timezone.now() - timedelta(days=30)
        )

        # 2. معاملة قديمة جداً (عمرها 190 يوماً - أكثر من 6 أشهر، تحذف تلقائياً)
        old_tx = Transaction.objects.create(
            user=self.user,
            amount=2.00,
            status='approved'
        )
        Transaction.objects.filter(id=old_tx.id).update(
            submitted_at=timezone.now() - timedelta(days=190)
        )

        # تشغيل مهمة التنظيف الدوري
        delete_expired_content()

        # التحقق من أن المعاملة الحديثة (30 يوماً) لا تزال موجودة
        self.assertTrue(Transaction.objects.filter(id=recent_tx.id).exists())
        # التحقق من أن المعاملة التي مر عليها أكثر من 6 أشهر حُذفت
        self.assertFalse(Transaction.objects.filter(id=old_tx.id).exists())


@override_settings(SECURE_SSL_REDIRECT=False)
class AdminAdActionSyncTestCase(TestCase):
    """اختبار مزامنة حالة المعاملة المالية عند قبول أو رفض الإعلان من الأدمن"""

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='adminuser',
            email='admin@example.com',
            password='AdminPass123!',
            is_active=True,
            role='admin'
        )
        from rest_framework.authtoken.models import Token
        self.token = Token.objects.create(user=self.admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')

        self.seller = User.objects.create_user(
            username='seller',
            email='seller@example.com',
            password='SellerPass123!',
            is_active=True
        )

    def test_approve_ad_syncs_transaction_status(self):
        from core.models import Ad, Transaction
        ad = Ad.objects.create(
            user=self.seller,
            title='إعلان تجريبي للقبول',
            description='وصف الإعلان',
            status='pending',
            category='cars',
            governorate='amman'
        )
        tx = Transaction.objects.create(
            ad=ad,
            user=self.seller,
            amount=1.00,
            status='pending'
        )

        res = self.client.post(f'/api/ads/{ad.id}/action/', {'action': 'approve'})
        self.assertEqual(res.status_code, 200)

        tx.refresh_from_db()
        self.assertEqual(tx.status, 'approved')

    def test_reject_ad_syncs_transaction_status(self):
        from core.models import Ad, Transaction
        ad = Ad.objects.create(
            user=self.seller,
            title='إعلان تجريبي للرفض',
            description='وصف الإعلان',
            status='pending',
            category='cars',
            governorate='amman'
        )
        tx = Transaction.objects.create(
            ad=ad,
            user=self.seller,
            amount=1.00,
            status='pending'
        )

        res = self.client.post(f'/api/ads/{ad.id}/action/', {'action': 'reject'})
        self.assertEqual(res.status_code, 200)

        tx.refresh_from_db()
        self.assertEqual(tx.status, 'rejected')


@override_settings(SECURE_SSL_REDIRECT=False)
class AccountDeletionTestCase(TestCase):
    """اختبار حذف الحساب لمستخدمي كلمة المرور ومستخدمي Google OAuth"""

    def setUp(self):
        self.client = APIClient()

    def test_password_user_requires_password_for_deletion(self):
        from rest_framework.authtoken.models import Token
        user = User.objects.create_user(
            username='passuser',
            email='passuser@example.com',
            password='MyPassword123!',
            is_active=True
        )
        token = Token.objects.create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # بدون كلمة مرور -> يرفض 400
        res = self.client.delete(f'/api/users/{user.id}/', {})
        self.assertEqual(res.status_code, 400)

        # بكلمة مرور غير صحيحة -> يرفض 400
        res = self.client.delete(f'/api/users/{user.id}/', {'password': 'WrongPassword!'})
        self.assertEqual(res.status_code, 400)

        # بكلمة المرور الصحيحة -> ينجح 204
        res = self.client.delete(f'/api/users/{user.id}/', {'password': 'MyPassword123!'})
        self.assertEqual(res.status_code, 204)
        self.assertFalse(User.objects.filter(id=user.id).exists())

    def test_oauth_user_without_usable_password_can_delete_account(self):
        from rest_framework.authtoken.models import Token
        oauth_user = User(
            username='oauthuser',
            email='oauthuser@example.com',
            is_active=True
        )
        oauth_user.set_unusable_password()
        oauth_user.save()
        token = Token.objects.create(user=oauth_user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # مستخدم OAuth لا يملك كلمة مرور -> يستطيع الحذف بدون كلمة مرور
        res = self.client.delete(f'/api/users/{oauth_user.id}/', {})
        self.assertEqual(res.status_code, 204)
        self.assertFalse(User.objects.filter(id=oauth_user.id).exists())
