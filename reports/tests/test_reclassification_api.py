from rest_framework import status
from unittest.mock import patch

from reports.models import RequestHistory
from .base import RequestTestCase


class ReclassificationApiTests(RequestTestCase):
    def test_staff_can_reclassify_request(self):
        self.client.force_authenticate(user=self.staff)

        data = {
            "category": self.other_category.id
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/reclassify/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.other_category)
        self.assertEqual(self.citizen_request.department, self.other_department)

        history = RequestHistory.objects.get(request=self.citizen_request)

        self.assertEqual(history.event_type, RequestHistory.EventType.RECLASSIFIED)
        self.assertEqual(history.old_category, self.category)
        self.assertEqual(history.new_category, self.other_category)
        self.assertEqual(history.old_department, self.department)
        self.assertEqual(history.new_department, self.other_department)
        self.assertEqual(history.changed_by, self.staff)

    def test_admin_can_reclassify_request(self):
        self.client.force_authenticate(user=self.admin)

        data = {
            "category": self.other_category.id
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/reclassify/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.other_category)
        self.assertEqual(self.citizen_request.department, self.other_department)

    def test_staff_cannot_reclassify_request_from_other_department(self):
        self.client.force_authenticate(user=self.staff)

        data = {
            "category": self.other_category.id
        }

        response = self.client.patch(
            f"/requests/{self.other_citizen_request2.id}/reclassify/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.other_citizen_request2.refresh_from_db()

        self.assertEqual(
            self.other_citizen_request2.category,
            self.other_category
        )
        self.assertEqual(
            self.other_citizen_request2.department,
            self.other_department
        )

    def test_citizen_cannot_reclassify_request(self):
        self.client.force_authenticate(user=self.citizen)

        data = {
            "category": self.other_category.id
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/reclassify/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)

        self.assertEqual(
            RequestHistory.objects.filter(
                request=self.citizen_request
            ).count(),
            0
        )

    def test_cannot_reclassify_to_same_category(self):
        self.client.force_authenticate(user=self.staff)

        data = {
            "category": self.category.id
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/reclassify/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)

        self.assertEqual(
            RequestHistory.objects.filter(
                request=self.citizen_request
            ).count(),
            0
        )

    def test_cannot_reclassify_to_nonexistent_category(self):
        self.client.force_authenticate(user=self.staff)

        data = {
            "category": 999999
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/reclassify/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)

        self.assertEqual(
            RequestHistory.objects.filter(
                request=self.citizen_request
            ).count(),
            0
        )

    def test_reclassification_rolls_back_if_history_creation_fails(self):
        self.client.force_authenticate(user=self.staff)

        data = {
            "category": self.other_category.id
        }

        with self.assertRaises(Exception):
            with patch(
                "reports.views.RequestHistory.objects.create",
                side_effect=Exception("Simulated error")
            ):
                self.client.patch(
                    f"/requests/{self.citizen_request.id}/reclassify/",
                    data=data,
                    format="json"
                )

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)

        self.assertEqual(
            RequestHistory.objects.filter(
                request=self.citizen_request
            ).count(),
            0
        )
