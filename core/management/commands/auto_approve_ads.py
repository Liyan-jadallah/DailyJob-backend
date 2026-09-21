from django.core.management.base import BaseCommand
from core.tasks import auto_approve_pending_ads


class Command(BaseCommand):
    help = 'Auto-approve pending ads that have a valid payment and have been pending for more than 10 minutes'

    def handle(self, *args, **options):
        result = auto_approve_pending_ads()
        self.stdout.write(self.style.SUCCESS(result))
