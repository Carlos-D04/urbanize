from unittest.mock import patch

from django.db import DatabaseError, transaction

from notifications.models import EmailDelivery, Notification
from reports.models import Request, RequestHistory
from reports.services import InvalidStatusTransition, change_request_status
from .base import RequestTestCase


class StatusServiceTests(RequestTestCase):
    def test_stale_request_cannot_repeat_a_committed_status_change(self):
        stale_request = Request.objects.get(pk=self.citizen_request.pk)
        change_request_status(self.citizen_request, Request.Status.IN_REVIEW, self.staff)

        with self.assertRaises(InvalidStatusTransition):
            change_request_status(stale_request, Request.Status.IN_REVIEW, self.staff)

        self.citizen_request.refresh_from_db()
        self.assertEqual(self.citizen_request.status, Request.Status.IN_REVIEW)
        self.assertEqual(RequestHistory.objects.filter(request=self.citizen_request).count(), 1)
        self.assertEqual(Notification.objects.filter(request=self.citizen_request).count(), 1)

    def test_service_rejects_skipped_status(self):

        old_status = self.citizen_request.status

        with self.assertRaises(InvalidStatusTransition):
            change_request_status(self.citizen_request, new_status = Request.Status.IN_PROGRESS, changed_by = self.staff)

        self.citizen_request.refresh_from_db()

        self.assertEqual(old_status, self.citizen_request.status)
        self.assertFalse(EmailDelivery.objects.exists())

    def test_service_changes_request_status(self):

        self.assertEqual(RequestHistory.objects.count(), 0)

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            change_request_status(self.citizen_request, Request.Status.IN_REVIEW, self.staff)
        self.assertEqual(callbacks, [])

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

                with self.captureOnCommitCallbacks(execute=True) as callbacks:
                    change_request_status(self.citizen_request, new_status, self.staff)
                    self.assertFalse(EmailDelivery.objects.filter(
                        notification__request=self.citizen_request, notification__new_status=new_status
                    ).exists())
                self.assertEqual(len(callbacks), 1)

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

    def test_status_change_survives_email_delivery_creation_failure(self):
        self.citizen_request.status = Request.Status.IN_REVIEW
        self.citizen_request.save()

        with patch(
            "notifications.services.EmailDelivery.objects.create",
            side_effect=DatabaseError("Simulated delivery failure"),
        ):
            with self.assertLogs("notifications.services", level="ERROR") as logs:
                with self.captureOnCommitCallbacks(execute=True):
                    change_request_status(self.citizen_request, Request.Status.IN_PROGRESS, self.staff)

        self.citizen_request.refresh_from_db()
        self.assertEqual(self.citizen_request.status, Request.Status.IN_PROGRESS)
        self.assertEqual(RequestHistory.objects.filter(request=self.citizen_request).count(), 1)
        self.assertEqual(Notification.objects.filter(request=self.citizen_request).count(), 1)
        self.assertFalse(EmailDelivery.objects.exists())
        self.assertIn("Simulated delivery failure", "\n".join(logs.output))

    def test_rollback_discards_scheduled_email_delivery(self):
        self.citizen_request.status = Request.Status.IN_REVIEW
        self.citizen_request.save(update_fields=["status"])

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with self.assertRaisesRegex(RuntimeError, "Roll back request changes"):
                with transaction.atomic():
                    change_request_status(self.citizen_request, Request.Status.IN_PROGRESS, self.staff)
                    raise RuntimeError("Roll back request changes")

        self.assertEqual(callbacks, [])
        self.citizen_request.refresh_from_db()
        self.assertEqual(self.citizen_request.status, Request.Status.IN_REVIEW)
        self.assertFalse(RequestHistory.objects.exists())
        self.assertFalse(Notification.objects.exists())
        self.assertFalse(EmailDelivery.objects.exists())
