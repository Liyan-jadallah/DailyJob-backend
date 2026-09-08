import os
from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .models import User, Notification

@shared_task
def send_global_notification_task(ad_id, ad_title, ad_owner_id, ad_category=''):
    results = []
    try:
        from .firebase_utils import send_topic_notification
        notification_title = "إعلان جديد! 📢"
        notification_body = f"تم نشر إعلان جديد: {ad_title}"
        data = {'ad_id': str(ad_id)}

        if ad_category and ad_category.strip():
            cat_topic = f"cat_{ad_category.strip()}"
            cat_success = send_topic_notification(topic=cat_topic, title=notification_title, body=notification_body, data=data)
            results.append(f"Category topic '{cat_topic}': {cat_success}")

        all_success = send_topic_notification(topic="all", title=notification_title, body=notification_body, data=data)
        results.append(f"Global topic 'all': {all_success}")

        return f"Notifications sent for Ad {ad_id}: {'; '.join(results)}"
    except Exception as e:
        print(f"Error sending global push to topics: {e}")
        return f"Failed to send global push for Ad {ad_id}: {e}"

@shared_task
def auto_approve_pending_ads():
    from .models import Ad
    grace_minutes = int(os.getenv('AD_AUTO_APPROVE_MINUTES', '10'))
    grace_period_cutoff = timezone.now() - timedelta(minutes=grace_minutes)

    pending_ads = Ad.objects.filter(status='pending', created_at__lt=grace_period_cutoff)
    approved_count = 0
    for ad in pending_ads:
        ad.status = 'approved'
        ad.save()
        approved_count += 1
    return f"Auto-approved {approved_count} ads (grace period: {grace_minutes} min)"

@shared_task
def delete_expired_content():
    from .models import Ad
    now = timezone.now()
    day_cutoff = now - timedelta(hours=24)
    week_cutoff = now - timedelta(days=7)

    deleted_day_ads, _ = Ad.objects.filter(status='approved', ad_duration='1_day', approved_at__lt=day_cutoff).delete()
    deleted_week_ads, _ = Ad.objects.filter(status='approved', ad_duration='1_week', approved_at__lt=week_cutoff).delete()

    notif_cutoff = now - timedelta(days=7)
    deleted_notifs, _ = Notification.objects.filter(created_at__lt=notif_cutoff).delete()

    return f"Deleted {deleted_day_ads} 1-day ads, {deleted_week_ads} 1-week ads, and {deleted_notifs} expired notifications (>7 days)"

@shared_task
def send_contact_email_task(name, email, subject, message):
    from django.core.mail import send_mail
    from django.conf import settings
    admin_email = getattr(settings, 'EMAIL_HOST_USER', None)
    if not admin_email:
        return "Email host user not configured in settings."
    full_subject = f"رسالة دعم جديدة: {subject or 'بدون عنوان'}"
    body = f"رسالة جديدة من التطبيق:\n\nالاسم: {name}\nالبريد: {email}\nالموضوع: {subject or 'لا يوجد'}\n\nالرسالة:\n{message}\n"
    try:
        send_mail(subject=full_subject, message=body, from_email=admin_email, recipient_list=[admin_email], fail_silently=False)
        return "Contact email sent successfully."
    except Exception as e:
        return f"Failed to send email: {e}"
