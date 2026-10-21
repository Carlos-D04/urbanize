from rest_framework import status
from unittest.mock import patch

from reports.models import Request, RequestHistory
from .base import RequestTestCase


class RequestApiTests(RequestTestCase):
    def test_staff_can_change_request_status(self):
        self.client.force_authenticate(user=self.staff)

        data = {"status": Request.Status.IN_REVIEW}

        self.assertEqual(RequestHistory.objects.count(), 0)

        response = self.client.patch(f"/requests/{self.citizen_request.id}/change-status/", data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.status, Request.Status.IN_REVIEW)

        self.assertEqual(RequestHistory.objects.count(), 1)

    def test_staff_cannot_skip_request_status(self):
        self.client.force_authenticate(user=self.staff)

        data = {"status": Request.Status.RESOLVED}

        self.assertEqual(RequestHistory.objects.count(), 0)

        response = self.client.patch(f"/requests/{self.citizen_request.id}/change-status/", data=data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.status, Request.Status.PENDING)

        self.assertEqual(RequestHistory.objects.count(), 0)

    def test_admin_can_change_request_status(self):
        self.client.force_authenticate(user=self.admin)

        data = {"status": Request.Status.IN_REVIEW}

        response = self.client.patch(f"/requests/{self.citizen_request.id}/change-status/", data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.status, Request.Status.IN_REVIEW)

        self.assertEqual(RequestHistory.objects.count(), 1)

    def test_cannot_change_to_invalid_status(self):
        self.client.force_authenticate(user=self.staff)

        data = {"status": "Banana"}

        response = self.client.patch(path=f"/requests/{self.citizen_request.id}/change-status/", data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.status, Request.Status.PENDING)

        self.assertEqual(RequestHistory.objects.count(), 0)

    def test_status_change_rolls_back_if_history_creation_fails(self):
        self.client.force_authenticate(user=self.staff)

        data = {"status": Request.Status.IN_REVIEW}

        with self.assertRaises(Exception):
            with patch("reports.views.RequestHistory.objects.create",side_effect = Exception("Simulated error")):
                self.client.patch(f"/requests/{self.citizen_request.id}/change-status/", data=data, format="json")

        self.citizen_request.refresh_from_db()


        self.assertEqual(self.citizen_request.status, Request.Status.PENDING)

        self.assertEqual(RequestHistory.objects.count(), 0)

    def test_can_check_own_request_history(self):
        self.client.force_authenticate(user = self.citizen)

        RequestHistory.objects.create(
            request=self.citizen_request,
            changed_by=self.staff,
            old_status=Request.Status.PENDING,
            new_status=Request.Status.IN_REVIEW
        )

        response = self.client.get(f"/requests/{self.citizen_request.id}/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 1)

        self.assertEqual(response.data[0]["old_status"],Request.Status.PENDING)
        self.assertEqual(response.data[0]["new_status"],Request.Status.IN_REVIEW)

    def test_request_without_history_returns_empty_list(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(f"/requests/{self.other_citizen_request.id}/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 0)

    def test_citizen_cannot_change_category(self):
        self.client.force_authenticate(user=self.citizen)

        data = {
            "category": self.other_category.id
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.citizen_request.refresh_from_db()

        self.assertEqual(
            self.citizen_request.category,
            self.category
        )

    def test_staff_cannot_change_category_through_regular_update(self):
        self.client.force_authenticate(user=self.staff)

        data = {
            "category": self.other_category.id
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

        self.citizen_request.refresh_from_db()

        self.assertEqual(
            self.citizen_request.category,
            self.category
        )
        self.assertEqual(self.citizen_request.department, self.department)

    def test_admin_cannot_change_category_through_regular_update(self):
        self.client.force_authenticate(user=self.admin)

        data = {
            "category": self.other_category.id
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)

        self.citizen_request.refresh_from_db()

        self.assertEqual(
            self.citizen_request.category,
            self.category
        )
        self.assertEqual(self.citizen_request.department, self.department)

    def test_regular_update_rejects_current_category_for_all_roles(self):
        for user in (self.citizen, self.staff, self.admin):
            for method in ("patch", "put"):
                with self.subTest(role=user.role, method=method):
                    self.client.force_authenticate(user=user)
                    data = {
                        "title": "Attempted title update",
                        "description": self.citizen_request.description,
                        "location": self.citizen_request.location,
                        "category": self.category.id,
                    }

                    response = getattr(self.client, method)(
                        f"/requests/{self.citizen_request.id}/",
                        data=data,
                        format="json",
                    )

                    self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                    self.assertIn("category", response.data)

                    self.citizen_request.refresh_from_db()
                    self.assertEqual(self.citizen_request.category, self.category)
                    self.assertEqual(self.citizen_request.department, self.department)
                    self.assertEqual(self.citizen_request.title, "Pothole on the street")

    def test_citizen_can_update_other_fields_without_changing_category(self):
        self.client.force_authenticate(user=self.citizen)

        data = {
            "title": "Updated title"
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.citizen_request.refresh_from_db()

        self.assertEqual(
            self.citizen_request.title,
            "Updated title"
        )

        self.assertEqual(
            self.citizen_request.category,
            self.category
        )
