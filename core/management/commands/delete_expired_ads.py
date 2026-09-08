from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Ad

class Command(BaseCommand):
    help = 'Deletes ads older than 24 hours'

    def handle(self, *args, **options):
        cutoff_time = timezone.now() - timedelta(hours=24)
        expired_ads = Ad.objects.filter(created_at__lt=cutoff_time)
        count, _ = expired_ads.delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} expired ads.'))
