from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department
from categories.models import Category
from .models import Request, RequestHistory


User = get_user_model()


class RequestAPITestCase(APITestCase):

    def setUp(self):
        self.citizen = User.objects.create_user(username="carlos", password="test123", role=User.Role.CITIZEN)

        self.other_citizen = User.objects.create_user(username="joao", password="test123", role=User.Role.CITIZEN)

        self.department = Department.objects.create(name="Infrastructure", description="Infrastructure Department")
        self.other_department = Department.objects.create(name="Public Lightning", description = "Public Lighting Department")

        self.category = Category.objects.create(
            name="Roads",
            description="Road problems", 
            department=self.department
            )
        
        self.other_category = Category.objects.create(
            name="Street Lighting", 
            description ="Problems related to public street lightning",
            department = self.other_department
            )

        self.staff = User.objects.create_user(username="John", password="test123", role=User.Role.STAFF, department = self.department)

        self.admin = User.objects.create_user(username="Ferdinand", password="test123", role=User.Role.ADMIN)

        self.citizen_request = Request.objects.create(
            author=self.citizen,
            category=self.category,
            department=self.department,
            title="Pothole on the street",
            description="Large pothole causing traffic problems",
            location="Aracaju"
        )

        self.other_citizen_request = Request.objects.create(
            author=self.other_citizen,
            category=self.category,
            department=self.department,
            title="Broken sidewalk",
            description="Sidewalk needs maintenance",
            location="Aracaju"
        )

        self.other_citizen_request2 = Request.objects.create(
                author=self.other_citizen,
                category=self.other_category,
                department=self.other_department,
                title="Broken street light",
                description="Street light is not working",
                location="Aracaju"
        )

    def test_citizen_can_only_see_own_requests(self):
        self.client.force_authenticate(user=self.citizen)

        response = self.client.get("/requests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        request_ids = [request["id"] for request in response.data]
        
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

        requests_id = [request["id"] for request in response.data]

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
        request_ids = [request["id"] for request in response.data]

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

    def test_citizen_cannot_change_request_status(self):
        self.client.force_authenticate(user=self.citizen)

        data = {"status": Request.Status.IN_REVIEW}

        self.assertEqual(RequestHistory.objects.count(), 0)
        
        response = self.client.patch(f"/requests/{self.citizen_request.id}/change-status/", data=data)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

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
        
        