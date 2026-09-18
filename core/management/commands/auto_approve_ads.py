from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from core.models import Ad


class Command(BaseCommand):
    help = 'Auto-approve pending ads that have a receipt and have been pending for more than 24 hours'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=24)
        pending_ads = Ad.objects.filter(
            status='pending',
            created_at__lte=cutoff,
            is_deleted=False
        ).exclude(
            transactions__receipt_image=''
        ).exclude(
            transactions__receipt_image__isnull=True
        )
        
        count = 0
        for ad in pending_ads:
            # Check if any transaction has a receipt
            has_receipt = ad.transactions.filter(
                receipt_image__isnull=False
            ).exclude(receipt_image='').exists()
            
            # Also check coupon-based transactions
            has_coupon = ad.transactions.filter(
                coupon__isnull=False
            ).exists()
            
            if has_receipt or has_coupon:
                ad.status = 'approved'
                ad.save(update_fields=['status'])
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Auto-approved {count} ads'))
