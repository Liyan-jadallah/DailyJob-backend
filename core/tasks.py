import os
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import User, Notification

@shared_task
def send_global_notification_task(ad_id, ad_title, ad_owner_id, ad_category='', ad_governorate=''):
    results = []
    notification_title = "إعلان جديد! 📢"
    notification_body = f"تم نشر إعلان جديد: {ad_title}"
    data = {'ad_id': str(ad_id)}

    try:
        from .firebase_utils import send_topic_notification, send_multicast_push_notification

        # 1. إرسال للموضوع العام "all" (يستقبله الزوار ومستخدمو التطبيق غير المسجلين)
        try:
            all_success = send_topic_notification(topic="all", title=notification_title, body=notification_body, data=data)
            results.append(f"Global topic 'all': {all_success}")
        except Exception as te:
            results.append(f"Global topic 'all' error: {te}")

        # 2. البحث عن كافة المستخدمين النشطين المفعلين للإشعارات باستثناء صاحب الإعلان
        eligible_users = User.objects.filter(
            notifications_enabled=True,
            is_active=True
        ).exclude(id=ad_owner_id)

        matching_tokens = set()
        in_app_notifs = []

        clean_cat = (ad_category or '').strip()
        clean_gov = (ad_governorate or '').strip()

        for u in eligible_users:
            matches = False
            if u.notify_all_ads:
                # المستخدم يرغب باستلام إشعارات لجميع الإعلانات
                matches = True
            else:
                # مستخدم مخصص: التحقق من مطابقة المحافظة والقسم
                govs = u.preferred_governorates or []
                cats = u.preferred_categories or []

                gov_matches = (not govs) or (clean_gov in govs)
                cat_matches = (not cats) or (clean_cat in cats)
                matches = gov_matches and cat_matches

            if matches:
                if u.fcm_token and u.fcm_token.strip():
                    matching_tokens.add(u.fcm_token.strip())
                in_app_notifs.append(
                    Notification(
                        user=u,
                        title=notification_title,
                        message=notification_body,
                        ad_id=ad_id
                    )
                )

        # 3. إرسال Push Notification مباشر لجميع الأجهزة المستهدفة لضمان الوصول الفوري
        if matching_tokens:
            direct_success = send_multicast_push_notification(
                tokens=list(matching_tokens),
                title=notification_title,
                body=notification_body,
                data=data
            )
            results.append(f"Direct push to {len(matching_tokens)} devices: {direct_success}")

        # 4. حفظ إشعارات داخل التطبيق لجميع المستخدمين المطابقين
        if in_app_notifs:
            Notification.objects.bulk_create(in_app_notifs, ignore_conflicts=True)
            results.append(f"Created {len(in_app_notifs)} in-app notifications")

        return f"Notifications sent for Ad {ad_id}: {'; '.join(results)}"
    except Exception as e:
        print(f"Error sending global push: {e}")
        return f"Failed to send global push for Ad {ad_id}: {e}"

@shared_task
def auto_approve_pending_ads():
    from .models import Ad, Transaction
    from django.db.models import Q
    grace_minutes = int(os.getenv('AD_AUTO_APPROVE_MINUTES', '10'))
    grace_period_cutoff = timezone.now() - timedelta(minutes=grace_minutes)

    # فقط الإعلانات المعلقة التي لها معاملة مع وصل دفع وتجاوزت فترة السماح
    pending_ads = Ad.objects.filter(status='pending', created_at__lt=grace_period_cutoff)
    approved_count = 0
    for ad in pending_ads:
        # التحقق من وجود معاملة مع وصل دفع أو كوبون مستخدم
        has_valid_transaction = Transaction.objects.filter(
            ad=ad
        ).filter(
            (Q(receipt_image__isnull=False) & ~Q(receipt_image='')) |
            Q(coupon__isnull=False)
        ).exists()
        if has_valid_transaction:
            ad.status = 'approved'
            ad.is_auto_approved = True
            ad.save()
            approved_count += 1
    return f"Auto-approved {approved_count} ads with valid payment (grace period: {grace_minutes} min)"

@shared_task
def delete_expired_content():
    from django.db.models import Q
    now = timezone.now()
    day_cutoff = now - timedelta(hours=24)
    week_cutoff = now - timedelta(days=7)

    deleted_day_ads, _ = Ad.objects.filter(
        Q(ad_duration='1_day') | Q(ad_duration__isnull=True) | Q(ad_duration=''),
        Q(approved_at__lt=day_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=day_cutoff))
    ).delete()
    deleted_week_ads, _ = Ad.objects.filter(
        Q(ad_duration='1_week'),
        Q(approved_at__lt=week_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=week_cutoff))
    ).delete()

    notif_cutoff = now - timedelta(days=7)
    deleted_notifs, _ = Notification.objects.filter(created_at__lt=notif_cutoff).delete()

    return f"Deleted {deleted_day_ads} 1-day ads, {deleted_week_ads} 1-week ads, and {deleted_notifs} expired notifications (>7 days)"

@shared_task
def send_contact_email_task(name, email, subject, message):
    from django.core.mail import send_mail
    from django.conf import settings
    admin_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', 'dailyjob2026@gmail.com'))
    if not admin_email:
        admin_email = 'dailyjob2026@gmail.com'
    full_subject = f"رسالة دعم جديدة: {subject or 'بدون عنوان'}"
    body = f"رسالة جديدة من التطبيق:\n\nالاسم: {name}\nالبريد: {email}\nالموضوع: {subject or 'لا يوجد'}\n\nالرسالة:\n{message}\n"
    try:
        send_mail(subject=full_subject, message=body, from_email=admin_email, recipient_list=[admin_email], fail_silently=False)
        return "Contact email sent successfully."
    except Exception as e:
        return f"Failed to send email: {e}"
