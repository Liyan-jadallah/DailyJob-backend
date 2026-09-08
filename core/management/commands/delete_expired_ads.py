from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from core.models import Ad

class Command(BaseCommand):
    help = 'Deletes expired ads (1-day ads after 24h, 1-week ads after 7 days)'

    def handle(self, *args, **options):
        now = timezone.now()
        day_cutoff = now - timedelta(hours=24)
        week_cutoff = now - timedelta(days=7)

        # 1-day ads (or default): expired after 24 hours
        day_expired = Ad.objects.filter(
            Q(ad_duration='1_day') | Q(ad_duration__isnull=True) | Q(ad_duration=''),
            Q(approved_at__lt=day_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=day_cutoff))
        )
        count_day, _ = day_expired.delete()

        # 1-week ads: expired after 7 days
        week_expired = Ad.objects.filter(
            Q(ad_duration='1_week'),
            Q(approved_at__lt=week_cutoff) | (Q(approved_at__isnull=True) & Q(created_at__lt=week_cutoff))
        )
        count_week, _ = week_expired.delete()

        total = count_day + count_week
        self.stdout.write(self.style.SUCCESS(
            f'Successfully deleted {total} expired ads ({count_day} 1-day, {count_week} 1-week).'
        ))
