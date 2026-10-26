from datetime import datetime, timedelta, timezone

from django.contrib.auth import get_user_model
from django.test import TestCase

from categories.models import Category
from departments.models import Department
from reports.models import Request
from ..models import EmailDelivery, Notification
from ..services import can_attempt_email_delivery

User = get_user_model()


class EmailDeliveryEligibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.now = datetime(2026, 10, 26, 15, 0, tzinfo=timezone.utc)
        cls.user = User.objects.create_user(
            username="recipient", email="recipient@example.com"
        )
        cls.other_user = User.objects.create_user(
            username="other", email="other@example.com"
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
        cls.other_request = Request.objects.create(
            author=cls.user, category=category, department=department,
            title="Sidewalk", description="Sidewalk needs repair", location="Aracaju",
        )
        notification = Notification.objects.create(
            recipient=cls.user, request=cls.request_obj,
            notification_type=Notification.NotificationType.RECLASSIFIED,
            title="Request reclassified", message="The category has changed.",
        )
        cls.delivery = EmailDelivery.objects.create(notification=notification)

    def create_previous_delivery(self, recipient, **fields):
        notification = Notification.objects.create(
            recipient=recipient, request=self.other_request,
            notification_type=Notification.NotificationType.STATUS_CHANGED,
            title="Request resolved", message="The request has been resolved.",
        )
        return EmailDelivery.objects.create(notification=notification, **fields)

    def test_new_pending_delivery_is_eligible(self):
        self.assertIs(can_attempt_email_delivery(self.delivery, self.now), True)

    def test_sent_delivery_is_not_eligible_even_after_interval(self):
        self.delivery.status = EmailDelivery.StatusType.SENT
        self.delivery.sent_at = self.now - timedelta(hours=1)
        self.delivery.save(update_fields=["status", "sent_at"])

        self.assertIs(can_attempt_email_delivery(self.delivery, self.now), False)

    def test_three_or_more_attempts_prevent_another_attempt(self):
        for attempts in (3, 4):
            with self.subTest(attempts=attempts):
                self.delivery.attempts = attempts
                self.delivery.save(update_fields=["attempts"])

                self.assertIs(can_attempt_email_delivery(self.delivery, self.now), False)

    def test_retry_interval_includes_exact_thirty_minute_boundary(self):
        for elapsed, expected in (
            (timedelta(minutes=30) - timedelta(microseconds=1), False),
            (timedelta(minutes=30), True),
            (timedelta(minutes=30, seconds=1), True),
        ):
            with self.subTest(elapsed=elapsed):
                self.delivery.status = EmailDelivery.StatusType.FAILED
                self.delivery.attempts = 2
                self.delivery.last_attempted_at = self.now - elapsed
                self.delivery.save(update_fields=["status", "attempts", "last_attempted_at"])

                self.assertIs(can_attempt_email_delivery(self.delivery, self.now), expected)

    def test_recent_send_for_same_user_blocks_across_requests(self):
        self.create_previous_delivery(
            self.user, status=EmailDelivery.StatusType.SENT,
            sent_at=self.now - timedelta(minutes=10),
        )

        self.assertIs(can_attempt_email_delivery(self.delivery, self.now), False)

    def test_successful_send_interval_includes_exact_thirty_minute_boundary(self):
        previous = self.create_previous_delivery(
            self.user, status=EmailDelivery.StatusType.SENT, sent_at=self.now,
        )
        for elapsed, expected in (
            (timedelta(minutes=30) - timedelta(microseconds=1), False),
            (timedelta(minutes=30), True),
            (timedelta(hours=1), True),
        ):
            with self.subTest(elapsed=elapsed):
                previous.sent_at = self.now - elapsed
                previous.save(update_fields=["sent_at"])

                self.assertIs(can_attempt_email_delivery(self.delivery, self.now), expected)

    def test_recent_send_for_another_user_does_not_block(self):
        self.create_previous_delivery(
            self.other_user, status=EmailDelivery.StatusType.SENT, sent_at=self.now,
        )

        self.assertIs(can_attempt_email_delivery(self.delivery, self.now), True)

    def test_failed_attempt_on_another_delivery_does_not_start_user_interval(self):
        self.create_previous_delivery(
            self.user, status=EmailDelivery.StatusType.FAILED,
            attempts=1, last_attempted_at=self.now - timedelta(minutes=1),
        )

        self.assertIs(can_attempt_email_delivery(self.delivery, self.now), True)

    def test_eligibility_check_does_not_modify_delivery(self):
        before = EmailDelivery.objects.values().get(pk=self.delivery.pk)

        can_attempt_email_delivery(self.delivery, self.now)

        self.assertEqual(EmailDelivery.objects.values().get(pk=self.delivery.pk), before)
