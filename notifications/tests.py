from datetime import timedelta

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from categories.models import Category
from departments.models import Department
from reports.models import Request
from .models import Notification

User = get_user_model()


class NotificationAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.department = Department.objects.create(
            name="Infrastructure", description="Infrastructure department"
        )
        cls.category = Category.objects.create(
            name="Roads", description="Road problems", department=cls.department
        )
        cls.users = {}
        for role in User.Role.values:
            cls.users[role] = User.objects.create_user(
                username=role.lower(), email=f"{role.lower()}@example.com",
                password="test-password", role=role, department=cls.department,
            )
        cls.citizen = cls.users[User.Role.CITIZEN]
        cls.request_obj = Request.objects.create(
            author=cls.citizen, category=cls.category, department=cls.department,
            title="Pothole", description="Road needs repair", location="Aracaju",
        )
        cls.notifications = {}
        for role, user in cls.users.items():
            cls.notifications[role] = Notification.objects.create(
                recipient=user, request=cls.request_obj,
                notification_type=Notification.NotificationType.STATUS_CHANGED,
                title="Request status updated", message="Your request is under review.",
                old_status=Request.Status.PENDING, new_status=Request.Status.IN_REVIEW,
            )
        cls.notification = cls.notifications[User.Role.CITIZEN]
        cls.other_notification = cls.notifications[User.Role.STAFF]
        cls.list_url = reverse("notification-list")

    def mark_read_url(self, notification):
        return reverse("notification-mark-as-read", args=[notification.pk])

    def test_each_role_lists_only_its_own_notifications(self):
        for role, user in self.users.items():
            with self.subTest(role=role):
                self.client.force_authenticate(user=user)

                response = self.client.get(self.list_url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.data["count"], 1)
                self.assertEqual(
                    [item["id"] for item in response.data["results"]],
                    [self.notifications[role].pk],
                )

    def test_listing_does_not_mark_notifications_as_read(self):
        self.client.force_authenticate(user=self.citizen)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["results"][0]["is_read"])
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)

    def test_notifications_are_ordered_by_newest_date_then_highest_id(self):
        self.client.force_authenticate(user=self.citizen)
        newer = Notification.objects.create(
            recipient=self.citizen, request=self.request_obj,
            notification_type=Notification.NotificationType.RECLASSIFIED,
            title="Request reclassified", message="The category has changed.",
        )
        newest = Notification.objects.create(
            recipient=self.citizen, request=self.request_obj,
            notification_type=Notification.NotificationType.RECLASSIFIED,
            title="Request reclassified again", message="The category has changed again.",
        )
        timestamp = timezone.now()
        Notification.objects.filter(pk__in=[self.notification.pk, newer.pk]).update(
            created_at=timestamp - timedelta(days=1)
        )
        Notification.objects.filter(pk=newest.pk).update(created_at=timestamp)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item["id"] for item in response.data["results"]],
            [newest.pk, newer.pk, self.notification.pk],
        )

    def test_user_can_mark_own_notification_as_read(self):
        self.client.force_authenticate(user=self.citizen)

        response = self.client.patch(self.mark_read_url(self.notification), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)
        self.other_notification.refresh_from_db()
        self.assertFalse(self.other_notification.is_read)

    def test_marking_an_already_read_notification_succeeds(self):
        self.client.force_authenticate(user=self.citizen)
        url = self.mark_read_url(self.notification)

        for attempt in range(2):
            with self.subTest(attempt=attempt):
                response = self.client.patch(url, {}, format="json")

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.notification.refresh_from_db()
                self.assertTrue(self.notification.is_read)

    def test_each_role_cannot_mark_another_users_notification_as_read(self):
        for role, user in self.users.items():
            with self.subTest(role=role):
                self.client.force_authenticate(user=user)
                target = (
                    self.other_notification if user.pk == self.citizen.pk
                    else self.notification
                )

                response = self.client.patch(self.mark_read_url(target), {}, format="json")

                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                target.refresh_from_db()
                self.assertFalse(target.is_read)

    def test_anonymous_user_cannot_list_notifications(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_anonymous_user_cannot_mark_notification_as_read(self):
        response = self.client.patch(self.mark_read_url(self.notification), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.notification.refresh_from_db()
        self.assertFalse(self.notification.is_read)
