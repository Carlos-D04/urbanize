from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from categories.models import Category
from departments.models import Department
from reports.models import Request
from notifications.models import EmailDelivery, Notification


class ProcessEmailDeliveriesTests(TestCase):
    def test_processes_candidates_in_order_and_reports_outcomes(self):
        user_model = get_user_model()
        author = user_model.objects.create_user(username="author", email="author@example.com")
        other = user_model.objects.create_user(username="other", email="other@example.com")
        department = Department.objects.create(name="Infrastructure")
        category = Category.objects.create(name="Roads", department=department)
        request = Request.objects.create(
            author=author, category=category, department=department,
            title="Pothole", description="Road needs repair", location="Aracaju",
        )

        def delivery_for(recipient, title, **fields):
            notification = Notification.objects.create(
                recipient=recipient, request=request,
                notification_type=Notification.NotificationType.RECLASSIFIED,
                title=title, message="The category has changed.",
            )
            return EmailDelivery.objects.create(notification=notification, **fields)

        states = EmailDelivery.StatusType
        retry = delivery_for(other, "Retry", status=states.FAILED, attempts=1,
                             last_attempted_at=timezone.now() - timedelta(hours=1))
        deferred = delivery_for(author, "Later update")
        first = delivery_for(author, "First update")
        timestamp = timezone.now()
        EmailDelivery.objects.filter(pk__in=[retry.pk, deferred.pk]).update(created_at=timestamp)
        EmailDelivery.objects.filter(pk=first.pk).update(created_at=timestamp - timedelta(minutes=1))
        exhausted = delivery_for(other, "Exhausted", status=states.FAILED, attempts=3)
        already_sent = delivery_for(other, "Already sent", status=states.SENT, attempts=1,
                                    sent_at=timestamp - timedelta(hours=1))
        output = StringIO()

        with patch("notifications.services.send_mail", side_effect=[1, 0]) as send_mail:
            call_command("process_email_deliveries", stdout=output)

        self.assertEqual([call.kwargs["subject"] for call in send_mail.call_args_list],
                         ["First update", "Retry"])
        self.assertIn("Sent: 1; Failed: 1; Skipped: 1", output.getvalue())
        for delivery, expected_state, attempts in (
            (first, states.SENT, 1), (retry, states.FAILED, 2),
            (deferred, states.PENDING, 0), (exhausted, states.FAILED, 3),
            (already_sent, states.SENT, 1),
        ):
            with self.subTest(delivery=delivery.pk):
                delivery.refresh_from_db()
                self.assertEqual((delivery.status, delivery.attempts), (expected_state, attempts))
