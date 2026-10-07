from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from core.models import Ad, Transaction

class Command(BaseCommand):
    help = 'Deletes expired ads (1-day ads after 24h, 1-week ads after 7 days)'

    def handle(self, *args, **options):
        now = timezone.now()
        day_cutoff = now - timedelta(hours=24)
        week_cutoff = now - timedelta(days=7)

        # 1-day ads (or default): expired after 24 hours of approval
        day_expired = Ad.objects.filter(
            status='approved'
        ).filter(
            Q(ad_duration='1_day') | Q(ad_duration__isnull=True) | Q(ad_duration='')
        ).filter(
            Q(approved_at__lt=day_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=day_cutoff))
        )
        count_day, _ = day_expired.delete()

        # 1-week ads: expired after 7 days of approval
        week_expired = Ad.objects.filter(
            status='approved',
            ad_duration='1_week'
        ).filter(
            Q(approved_at__lt=week_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=week_cutoff))
        )
        count_week, _ = week_expired.delete()

        total = count_day + count_week
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {total} expired ads ({count_day} 1-day, {count_week} 1-week).'
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
