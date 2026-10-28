from rest_framework import status

from categories.models import Category
from reports.models import RequestHistory
from reports.services import change_classified
from .base import RequestTestCase


class RequestHistoryApiTests(RequestTestCase):
    def test_history_exposes_reclassification_between_departments(self):
        change_classified(self.citizen_request, self.other_category, self.staff)
        self.client.force_authenticate(user=self.citizen)

        response = self.client.get(f"/requests/{self.citizen_request.pk}/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        event = response.data[0]
        self.assertEqual(event["event_type"], RequestHistory.EventType.RECLASSIFIED)
        self.assertEqual(event["request"], self.citizen_request.pk)
        self.assertEqual(event["changed_by"], {"id": self.staff.pk, "username": self.staff.username})
        self.assertEqual(event["old_category"], self.category.pk)
        self.assertEqual(event["new_category"], self.other_category.pk)
        self.assertEqual(event["old_department"], self.department.pk)
        self.assertEqual(event["new_department"], self.other_department.pk)

    def test_history_exposes_reclassification_within_same_department(self):
        new_category = Category.objects.create(
            name="Sidewalks", description="Sidewalk problems", department=self.department
        )
        change_classified(self.citizen_request, new_category, self.staff)
        self.client.force_authenticate(user=self.citizen)

        response = self.client.get(f"/requests/{self.citizen_request.pk}/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        event = response.data[0]
        self.assertEqual(event["event_type"], RequestHistory.EventType.RECLASSIFIED)
        self.assertEqual(event["changed_by"]["id"], self.staff.pk)
        self.assertEqual(event["old_category"], self.category.pk)
        self.assertEqual(event["new_category"], new_category.pk)
        self.assertEqual(event["old_department"], self.department.pk)
        self.assertEqual(event["new_department"], self.department.pk)
