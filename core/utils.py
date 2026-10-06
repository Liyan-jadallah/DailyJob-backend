"""
وحدة الدوال المساعدة المشتركة — لمنع تكرار الكود في views.py
"""
import re
import secrets
import logging

from django.core.cache import cache
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_secure_otp():
    """توليد رمز OTP عشوائي وآمن تشفيرياً مكون من 6 خانات (100000-999999)"""
    return f"{secrets.randbelow(900000) + 100000}"


def sanitize_email(email_str):
    """تنظيف البريد الإلكتروني من المحارف الخفية والمسافات"""
    return re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff\s]', '', str(email_str or '')).lower()


def normalize_otp(raw_otp):
    """تحويل الأرقام العربية/الفارسية إلى أرقام إنجليزية في رمز OTP"""
    arabic_digits = '٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹'
    english_digits = '01234567890123456789'
    trans_table = str.maketrans(arabic_digits, english_digits)
    return str(raw_otp).strip().translate(trans_table)


def get_from_email():
    """جلب بريد المرسل الافتراضي من الإعدادات"""
    return getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', ''))


def send_and_cache_otp(email, username, cache_prefix='verify', subject='رمز تأكيد حسابك - Daily Job', purpose='تأكيد حسابك'):
    """
    توليد رمز OTP، تخزينه في الكاش، وإرساله عبر البريد الإلكتروني.
    يُستخدم لتوحيد المنطق في التسجيل، إعادة الإرسال، واستعادة كلمة المرور.
    
    Returns: (otp_code, email_sent)
    """
    otp_code = generate_secure_otp()
    clean_email = sanitize_email(email)
    cache.set(f'{cache_prefix}_{clean_email}', otp_code, timeout=600)
    
    email_sent = False
    try:
        from core.views import send_otp_email
        send_otp_email(
            to_email=clean_email,
            username=username,
            otp_code=otp_code,
            subject=subject,
            purpose=purpose
        )
        email_sent = True
    except Exception as e:
        logger.warning(f"[OTP] Failed to send OTP to {clean_email}: {e}")
    
    return otp_code, email_sent


def is_admin_user(user):
    """التحقق من صلاحيات الأدمن بشكل موحد"""
    if not user or not user.is_authenticated:
        return False
    return (
        getattr(user, 'role', '') == 'admin'
        or user.is_staff
        or user.is_superuser
    )
