from django.core.management.base import BaseCommand

from notifications.models import EmailDelivery
from notifications.services import attempt_email_delivery


class Command(BaseCommand):
    help = "Process pending email deliveries."

    def handle(self, *args, **options):
        deliveries = EmailDelivery.objects.filter(
            status__in=(EmailDelivery.StatusType.PENDING, EmailDelivery.StatusType.FAILED),
            attempts__lt=3,
        ).select_related("notification").order_by("created_at", "pk")
        totals = {"sent": 0, "failed": 0, "skipped": 0, "expired": 0}
        for delivery in deliveries.iterator():
            totals[attempt_email_delivery(delivery)] += 1

        self.stdout.write(
            f"Sent: {totals['sent']}; Failed: {totals['failed']}; Skipped: {totals['skipped']}"
            f"; Expired: {totals['expired']}"
        )
