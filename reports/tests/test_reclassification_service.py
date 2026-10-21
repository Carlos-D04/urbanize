from unittest.mock import patch

from categories.models import Category
from notifications.models import Notification
from reports.models import Request, RequestHistory
from reports.services import InvalidCategoryChange, change_classified
from .base import RequestTestCase


class ReclassificationServiceTests(RequestTestCase):
    def test_service_reclassifies_request(self):
        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)
        self.assertEqual(RequestHistory.objects.count(), 0)

        change_classified(
            self.citizen_request,
            self.other_category,
            self.staff
        )

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.other_category)
        self.assertEqual(self.citizen_request.department, self.other_department)

        self.assertEqual(RequestHistory.objects.count(), 1)

        history = RequestHistory.objects.get(request=self.citizen_request)

        self.assertEqual(history.event_type, RequestHistory.EventType.RECLASSIFIED)
        self.assertEqual(history.changed_by, self.staff)
        self.assertEqual(history.old_category, self.category)
        self.assertEqual(history.new_category, self.other_category)
        self.assertEqual(history.old_department, self.department)
        self.assertEqual(history.new_department, self.other_department)

        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.get(request=self.citizen_request)
        self.assertEqual(notification.recipient, self.citizen)
        self.assertEqual(notification.notification_type, Notification.NotificationType.RECLASSIFIED)
        self.assertEqual(notification.old_category, self.category)
        self.assertEqual(notification.new_category, self.other_category)
        self.assertEqual(notification.old_department, self.department)
        self.assertEqual(notification.new_department, self.other_department)
        self.assertFalse(notification.is_read)
        self.assertTrue(notification.title)
        self.assertIn(self.citizen_request.title, notification.message)
        self.assertIn(self.category.name, notification.message)
        self.assertIn(self.other_category.name, notification.message)
        self.assertIn(self.other_department.name, notification.message)

    def test_reclassification_within_same_department_notifies_author(self):
        new_category = Category.objects.create(
            name="Sidewalks", description="Sidewalk problems", department=self.department
        )

        change_classified(self.citizen_request, new_category, self.staff)

        self.citizen_request.refresh_from_db()
        self.assertEqual(self.citizen_request.category, new_category)
        self.assertEqual(self.citizen_request.department, self.department)
        self.assertEqual(Notification.objects.count(), 1)
        notification = Notification.objects.get(request=self.citizen_request)
        self.assertEqual(notification.recipient, self.citizen)
        self.assertEqual(notification.old_category, self.category)
        self.assertEqual(notification.new_category, new_category)
        self.assertEqual(notification.old_department, self.department)
        self.assertEqual(notification.new_department, self.department)

    def test_reclassification_by_author_does_not_notify(self):
        self.citizen_request.author = self.admin
        self.citizen_request.save()

        change_classified(self.citizen_request, self.other_category, self.admin)

        self.citizen_request.refresh_from_db()
        self.assertEqual(self.citizen_request.category, self.other_category)
        self.assertEqual(self.citizen_request.department, self.other_department)
        self.assertEqual(RequestHistory.objects.filter(request=self.citizen_request).count(), 1)
        self.assertFalse(Notification.objects.exists())

    def test_reclassification_notifies_without_changing_status_at_any_stage(self):
        for request_status in Request.Status.values:
            with self.subTest(status=request_status):
                request_obj = Request.objects.create(
                    author=self.citizen, category=self.category,
                    department=self.department, title="Request to reclassify",
                    description="Description", location="Aracaju", status=request_status,
                )

                change_classified(request_obj, self.other_category, self.staff)

                request_obj.refresh_from_db()
                self.assertEqual(request_obj.status, request_status)
                self.assertEqual(request_obj.category, self.other_category)
                notifications = Notification.objects.filter(request=request_obj)
                self.assertEqual(notifications.count(), 1)
                self.assertEqual(notifications.get().recipient, self.citizen)

    def test_reclassification_rolls_back_if_notification_creation_fails(self):
        original_updated_at = self.citizen_request.updated_at
        with patch(
            "notifications.services.Notification.objects.create",
            side_effect=RuntimeError("Simulated notification failure"),
        ):
            with self.assertRaisesRegex(RuntimeError, "Simulated notification failure"):
                change_classified(self.citizen_request, self.other_category, self.staff)

        self.citizen_request.refresh_from_db()
        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)
        self.assertEqual(self.citizen_request.status, Request.Status.PENDING)
        self.assertEqual(self.citizen_request.updated_at, original_updated_at)
        self.assertFalse(RequestHistory.objects.exists())
        self.assertFalse(Notification.objects.exists())

    def test_service_rejects_same_category(self):
        self.assertEqual(RequestHistory.objects.count(), 0)

        self.assertFalse(Notification.objects.exists())

        with self.assertRaises(InvalidCategoryChange):
            change_classified(
                self.citizen_request,
                self.category,
                self.staff
            )

        self.citizen_request.refresh_from_db()
        self.assertFalse(Notification.objects.exists())

        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)

        self.assertEqual(RequestHistory.objects.count(), 0)

    def test_reclassification_rolls_back_if_history_creation_fails(self):
        with self.assertRaises(Exception):
            with patch(
                "reports.services.RequestHistory.objects.create",
                side_effect=Exception("Simulated error")
            ):
                change_classified(
                    self.citizen_request,
                    self.other_category,
                    self.staff
                )

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)

        self.assertEqual(RequestHistory.objects.count(), 0)
