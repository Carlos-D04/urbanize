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

        request_ids = [request["id"]for request in response.data]

        self.assertIn(self.citizen_request.id,request_ids)

        self.assertNotIn(self.other_citizen_request.id,request_ids)