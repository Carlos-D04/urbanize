from rest_framework import status

from reports.models import Request, RequestHistory
from .base import RequestTestCase


class RequestPermissionsTests(RequestTestCase):
    def test_citizen_can_only_see_own_requests(self):
        self.client.force_authenticate(user=self.citizen)

        response = self.client.get("/requests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request_ids = [request["id"] for request in response.data["results"]]

        self.assertIn(self.citizen_request.id,request_ids)

        self.assertNotIn(self.other_citizen_request.id,request_ids)

    def test_citizen_can_edit_own_pending_request(self):

        self.client.force_authenticate(user=self.citizen)

        data = {
            "title": "New title"
        }

        response = self.client.patch(path = f"/requests/{self.citizen_request.id}/", data=data, format="json" )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.title, data["title"])

    def test_citizen_cannot_edit_own_non_pending_request(self):
        self.citizen_request.status = Request.Status.IN_REVIEW
        self.citizen_request.save()

        self.client.force_authenticate(user=self.citizen)

        data = {"title": "New title"}

        response = self.client.patch(path = f"/requests/{self.citizen_request.id}/", data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.title, "Pothole on the street")

    def test_citizen_cannot_edit_another_citizen_request(self):
        self.client.force_authenticate(user=self.citizen)

        data = {"title": "New title"}

        response = self.client.patch(path=f"/requests/{self.other_citizen_request.id}/", data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.other_citizen_request.refresh_from_db()

        self.assertEqual(self.other_citizen_request.title, "Broken sidewalk")

    def test_staff_can_only_see_requests_from_own_department(self):
        self.client.force_authenticate(user = self.staff)

        response = self.client.get("/requests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        requests_id = [request["id"] for request in response.data["results"]]

        self.assertIn(self.citizen_request.id, requests_id)

        self.assertNotIn(self.other_citizen_request2.id, requests_id)

    def test_staff_can_edit_request_from_own_department(self):
        self.client.force_authenticate(user=self.staff)

        data = {"title": "Big Title"}

        response = self.client.patch(f"/requests/{self.citizen_request.id}/", data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.title, "Big Title")

    def test_staff_cannot_edit_request_from_other_department(self):
        self.client.force_authenticate(user=self.staff)

        data={"title": "Super Big Giant Title"}

        response = self.client.patch(f"/requests/{self.other_citizen_request2.id}/", data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.other_citizen_request2.refresh_from_db()

        self.assertEqual(self.other_citizen_request2.title, "Broken street light")

    def test_admin_can_see_requests_from_all_departments(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get("/requests/")
        request_ids = [request["id"] for request in response.data["results"]]

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn(self.citizen_request.id, request_ids)
        self.assertIn(self.other_citizen_request2.id, request_ids)

    def test_admin_can_edit_request_from_any_department(self):
        self.client.force_authenticate(user=self.admin)

        data = {"title": "Super cool title"}

        response = self.client.patch(f"/requests/{self.other_citizen_request2.id}/", data=data, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.other_citizen_request2.refresh_from_db()

        self.assertEqual(self.other_citizen_request2.title, "Super cool title")

    def test_citizen_cannot_change_request_status(self):
        self.client.force_authenticate(user=self.citizen)

        data = {"status": Request.Status.IN_REVIEW}

        self.assertEqual(RequestHistory.objects.count(), 0)

        response = self.client.patch(f"/requests/{self.citizen_request.id}/change-status/", data=data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.status, Request.Status.PENDING)

        self.assertEqual(RequestHistory.objects.count(), 0)

    def test_other_citizen_cannot_check_request_history(self):
        self.client.force_authenticate(user=self.other_citizen)

        response = self.client.get(f"/requests/{self.citizen_request.id}/history/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_staff_can_check_own_department_request_history(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(f"/requests/{self.citizen_request.id}/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_cannot_check_other_department_request_history(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(f"/requests/{self.other_citizen_request2.id}/history/")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_admin_can_check_any_request_history(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(f"/requests/{self.other_citizen_request.id}/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
