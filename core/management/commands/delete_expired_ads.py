from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from core.models import Ad, Transaction, Notification, SystemSetting

class Command(BaseCommand):
    help = 'Deletes expired ads (1-day ads after 24h, 1-week ads after 7 days) and old notifications based on system settings'

    def handle(self, *args, **options):
        now = timezone.now()
        ad_days = SystemSetting.get_int('ad_retention_days', default=7)
        notif_days = SystemSetting.get_int('notification_retention_days', default=7)

        day_cutoff = now - timedelta(hours=24)
        week_cutoff = now - timedelta(days=ad_days)

        # 1-day ads: expired after 24 hours of approval
        day_expired = Ad.objects.filter(
            status='approved'
        ).filter(
            Q(ad_duration='1_day') | Q(ad_duration__isnull=True) | Q(ad_duration='')
        ).filter(
            Q(approved_at__lt=day_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=day_cutoff))
        )
        count_day, _ = day_expired.delete()

        # 1-week ads: expired ONLY after 7 days of approval (or ad_days)
        week_expired = Ad.objects.filter(
            status='approved',
            ad_duration='1_week'
        ).filter(
            Q(approved_at__lt=week_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=week_cutoff))
        )
        count_week, _ = week_expired.delete()

        total = count_day + count_week
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {total} expired ads ({count_day} 1-day, {count_week} 1-week older than {ad_days} days).'
        ))

        # حذف الإشعارات القديمة حسب إعدادات النظام
        notif_cutoff = now - timedelta(days=notif_days)
        deleted_notifs, _ = Notification.objects.filter(created_at__lt=notif_cutoff).delete()
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {deleted_notifs} notifications older than {notif_days} days.'
        ))

        # حذف المعاملات المالية التي مر عليها أكثر من 6 أشهر (180 يوماً)
        tx_cutoff = now - timedelta(days=180)
        old_txs = Transaction.objects.filter(submitted_at__lt=tx_cutoff)
        deleted_tx_count = 0
        for tx in old_txs.iterator():
            if tx.receipt_image:
                try:
                    if tx.receipt_image.storage.exists(tx.receipt_image.name):
                        tx.receipt_image.storage.delete(tx.receipt_image.name)
                except Exception:
                    pass
            tx.delete()
            deleted_tx_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {deleted_tx_count} transactions older than 6 months.'
        ))
