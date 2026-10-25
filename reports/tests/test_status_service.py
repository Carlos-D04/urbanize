from unittest.mock import patch

from notifications.models import EmailDelivery, Notification
from reports.models import Request, RequestHistory
from reports.services import InvalidStatusTransition, change_request_status
from .base import RequestTestCase


class StatusServiceTests(RequestTestCase):
    def test_service_rejects_skipped_status(self):

        old_status = self.citizen_request.status

        with self.assertRaises(InvalidStatusTransition):
            change_request_status(self.citizen_request, new_status = Request.Status.IN_PROGRESS, changed_by = self.staff)

        self.citizen_request.refresh_from_db()

        self.assertEqual(old_status, self.citizen_request.status)
        self.assertFalse(EmailDelivery.objects.exists())

    def test_service_changes_request_status(self):

        self.assertEqual(RequestHistory.objects.count(), 0)

        change_request_status(self.citizen_request, Request.Status.IN_REVIEW, changed_by = self.staff)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.status, Request.Status.IN_REVIEW)

        self.assertEqual(RequestHistory.objects.count(), 1)
        history = RequestHistory.objects.get(request = self.citizen_request)

        self.assertEqual(history.request, self.citizen_request)
        self.assertEqual(history.changed_by, self.staff)
        self.assertEqual(history.old_status, Request.Status.PENDING)
        self.assertEqual(history.new_status, Request.Status.IN_REVIEW)

        notification = Notification.objects.get(request=self.citizen_request)
        self.assertFalse(EmailDelivery.objects.filter(notification=notification).exists())

    def test_eligible_status_changes_create_pending_email_deliveries(self):
        for old_status, new_status in (
            (Request.Status.IN_REVIEW, Request.Status.IN_PROGRESS),
            (Request.Status.IN_PROGRESS, Request.Status.RESOLVED),
        ):
            with self.subTest(new_status=new_status):
                self.citizen_request.status = old_status
                self.citizen_request.save(update_fields=["status"])

                change_request_status(self.citizen_request, new_status, self.staff)

                self.citizen_request.refresh_from_db()
                self.assertEqual(self.citizen_request.status, new_status)
                notification = Notification.objects.get(
                    request=self.citizen_request, new_status=new_status
                )
                delivery = EmailDelivery.objects.get(notification=notification)
                self.assertEqual(delivery.status, EmailDelivery.StatusType.PENDING)
                self.assertEqual(delivery.attempts, 0)
                self.assertIsNone(delivery.last_attempted_at)
                self.assertIsNone(delivery.sent_at)
                self.assertEqual(delivery.last_error, "")
                self.assertEqual(
                    EmailDelivery.objects.filter(notification=notification).count(), 1
                )

    def test_status_change_rolls_back_if_email_delivery_creation_fails(self):
        self.citizen_request.status = Request.Status.IN_REVIEW
        self.citizen_request.save()
        original_updated_at = self.citizen_request.updated_at

        with patch(
            "notifications.services.EmailDelivery.objects.create",
            side_effect=RuntimeError("Simulated delivery failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Simulated delivery failure"):
                change_request_status(
                    self.citizen_request, Request.Status.IN_PROGRESS, self.staff
                )

        self.citizen_request.refresh_from_db()
        self.assertEqual(self.citizen_request.status, Request.Status.IN_REVIEW)
        self.assertEqual(self.citizen_request.updated_at, original_updated_at)
        self.assertFalse(RequestHistory.objects.exists())
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(EmailDelivery.objects.exists())
