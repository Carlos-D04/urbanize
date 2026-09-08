from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase

from departments.models import Department
from categories.models import Category
from .models import Request


User = get_user_model()


class RequestAPITestCase(APITestCase):

    def setUp(self):
        self.citizen = User.objects.create_user(username="carlos",password="test123",role=User.Role.CITIZEN)

        self.other_citizen = User.objects.create_user(username="joao",password="test123",role=User.Role.CITIZEN)

        self.department = Department.objects.create(name="Infrastructure",description="Infrastructure Department")

        self.category = Category.objects.create(name="Roads",description="Road problems",department=self.department )

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

    def test_citizen_can_only_see_own_requests(self):
        self.client.force_authenticate(user=self.citizen)

        response = self.client.get("/requests/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        #pegando todos os ids das requests retornadas
        request_ids = [request["id"] for request in response.data]
        #verifica se A está dentro de B
        self.assertIn(self.citizen_request.id,request_ids)
        #verifica se A não está dentro de B
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
    