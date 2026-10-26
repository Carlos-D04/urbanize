from datetime import datetime, timedelta, timezone
from smtplib import SMTPException
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from categories.models import Category
from departments.models import Department
from reports.models import Request
from ..models import EmailDelivery, Notification
from ..services import attempt_email_delivery

User = get_user_model()


class EmailDeliveryAttemptTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.now = datetime(2026, 10, 26, 15, 0, tzinfo=timezone.utc)
        cls.user = User.objects.create_user(
            username="recipient", email="recipient@example.com"
        )
        department = Department.objects.create(
            name="Infrastructure", description="Infrastructure department"
        )
        category = Category.objects.create(
            name="Roads", description="Road problems", department=department
        )
        cls.request_obj = Request.objects.create(
            author=cls.user, category=category, department=department,
            title="Pothole", description="Road needs repair", location="Aracaju",
        )
        cls.notification = Notification.objects.create(
            recipient=cls.user, request=cls.request_obj,
            notification_type=Notification.NotificationType.RECLASSIFIED,
            title="Request reclassified", message="The category has changed.",
        )
        cls.delivery = EmailDelivery.objects.create(notification=cls.notification)

    def test_success_records_attempt_and_confirmation_time(self):
        confirmed_at = self.now + timedelta(seconds=5)
        with patch("notifications.services.timezone.now", side_effect=[self.now, confirmed_at]):
            with patch("notifications.services.send_mail", return_value=1) as send:
                result = attempt_email_delivery(self.delivery)

        self.assertEqual(result, "sent")
        send.assert_called_once_with(
            subject=self.notification.title, message=self.notification.message,
            from_email=None, recipient_list=[self.user.email],
        )
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, EmailDelivery.StatusType.SENT)
        self.assertEqual(self.delivery.attempts, 1)
        self.assertEqual(self.delivery.last_attempted_at, self.now)
        self.assertEqual(self.delivery.sent_at, confirmed_at)
        self.assertEqual(self.delivery.last_error, "")

    def test_successful_retry_increments_existing_count_and_clears_error(self):
        self.delivery.status = EmailDelivery.StatusType.FAILED
        self.delivery.attempts = 2
        self.delivery.last_attempted_at = self.now - timedelta(minutes=30)
        self.delivery.last_error = "Previous connection failure"
        self.delivery.save()

        with patch("notifications.services.timezone.now", return_value=self.now):
            with patch("notifications.services.send_mail", return_value=1) as send:
                result = attempt_email_delivery(self.delivery)

        self.assertEqual(result, "sent")
        send.assert_called_once()
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, EmailDelivery.StatusType.SENT)
        self.assertEqual(self.delivery.attempts, 3)
        self.assertEqual(self.delivery.last_error, "")
        self.assertEqual(self.delivery.sent_at, self.now)

    def test_zero_messages_sent_records_failure(self):
        with patch("notifications.services.timezone.now", return_value=self.now):
            with patch("notifications.services.send_mail", return_value=0) as send:
                result = attempt_email_delivery(self.delivery)

        self.assertEqual(result, "failed")
        send.assert_called_once()
        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.status, EmailDelivery.StatusType.FAILED)
        self.assertEqual(self.delivery.attempts, 1)
        self.assertEqual(self.delivery.last_attempted_at, self.now)
        self.assertIsNone(self.delivery.sent_at)
        self.assertEqual(self.delivery.last_error, "Email backend reported no messages sent.")

    def test_communication_errors_record_failure(self):
        for error in (SMTPException("SMTP unavailable"), OSError("Connection refused")):
            with self.subTest(error=type(error).__name__):
                self.delivery.status = EmailDelivery.StatusType.PENDING
                self.delivery.attempts = 0
                self.delivery.last_attempted_at = None
                self.delivery.last_error = ""
                self.delivery.save()

                with patch("notifications.services.timezone.now", return_value=self.now):
                    with patch("notifications.services.send_mail", side_effect=error) as send:
                        result = attempt_email_delivery(self.delivery)

                self.assertEqual(result, "failed")
                send.assert_called_once()
                self.delivery.refresh_from_db()
                self.assertEqual(self.delivery.status, EmailDelivery.StatusType.FAILED)
                self.assertEqual(self.delivery.attempts, 1)
                self.assertEqual(self.delivery.last_attempted_at, self.now)
                self.assertEqual(self.delivery.last_error, str(error))
                self.assertIsNone(self.delivery.sent_at)

    def test_blocked_deliveries_are_not_sent_or_modified(self):
        cases = (
            (EmailDelivery.StatusType.SENT, 1, self.now - timedelta(hours=1)),
            (EmailDelivery.StatusType.FAILED, 3, self.now - timedelta(hours=1)),
            (EmailDelivery.StatusType.FAILED, 1, self.now - timedelta(minutes=10)),
        )
        for delivery_status, attempts, last_attempt in cases:
            with self.subTest(status=delivery_status, attempts=attempts):
                self.delivery.status = delivery_status
                self.delivery.attempts = attempts
                self.delivery.last_attempted_at = last_attempt
                self.delivery.sent_at = last_attempt if delivery_status == EmailDelivery.StatusType.SENT else None
                self.delivery.save()
                before = EmailDelivery.objects.values().get(pk=self.delivery.pk)

                with patch("notifications.services.timezone.now", return_value=self.now):
                    with patch("notifications.services.send_mail") as send:
                        result = attempt_email_delivery(self.delivery)

                self.assertEqual(result, "skipped")
                send.assert_not_called()
                self.assertEqual(EmailDelivery.objects.values().get(pk=self.delivery.pk), before)

    def test_recent_send_to_same_user_skips_without_modifying_delivery(self):
        previous_notification = Notification.objects.create(
            recipient=self.user, request=self.request_obj,
            notification_type=Notification.NotificationType.STATUS_CHANGED,
            title="Request in progress", message="Work has started.",
        )
        EmailDelivery.objects.create(
            notification=previous_notification, status=EmailDelivery.StatusType.SENT,
            attempts=1, sent_at=self.now - timedelta(minutes=10),
        )
        before = EmailDelivery.objects.values().get(pk=self.delivery.pk)

        with patch("notifications.services.timezone.now", return_value=self.now):
            with patch("notifications.services.send_mail") as send:
                result = attempt_email_delivery(self.delivery)

        self.assertEqual(result, "skipped")
        send.assert_not_called()
        self.assertEqual(EmailDelivery.objects.values().get(pk=self.delivery.pk), before)

    def test_send_uses_current_email_even_when_recipient_is_cached(self):
        cached_delivery = EmailDelivery.objects.select_related("notification__recipient").get(
            pk=self.delivery.pk
        )
        User.objects.filter(pk=self.user.pk).update(email="updated@example.com")
        self.assertEqual(cached_delivery.notification.recipient.email, "recipient@example.com")

        with patch("notifications.services.timezone.now", return_value=self.now):
            with patch("notifications.services.send_mail", return_value=1) as send:
                result = attempt_email_delivery(cached_delivery)

        self.assertEqual(result, "sent")
        self.assertEqual(send.call_args.kwargs["recipient_list"], ["updated@example.com"])

    def test_unexpected_programming_error_is_not_swallowed(self):
        with patch("notifications.services.timezone.now", return_value=self.now):
            with patch("notifications.services.send_mail", side_effect=TypeError("Invalid argument")):
                with self.assertRaisesRegex(TypeError, "Invalid argument"):
                    attempt_email_delivery(self.delivery)

        self.delivery.refresh_from_db()
        self.assertEqual(self.delivery.attempts, 1)
        self.assertEqual(self.delivery.last_attempted_at, self.now)
        self.assertNotEqual(self.delivery.status, EmailDelivery.StatusType.SENT)
        self.assertIsNone(self.delivery.sent_at)
