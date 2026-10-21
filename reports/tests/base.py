from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from categories.models import Category
from departments.models import Department
from reports.models import Request

User = get_user_model()


class RequestTestCase(APITestCase):
    def setUp(self):
        self.citizen = User.objects.create_user(username="carlos", email="carlos@example.com", password="test123", role=User.Role.CITIZEN)

        self.other_citizen = User.objects.create_user(username="joao", email="joao@example.com", password="test123", role=User.Role.CITIZEN)

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

        self.staff = User.objects.create_user(username="John", email="john@example.com", password="test123", role=User.Role.STAFF, department = self.department)

        self.admin = User.objects.create_user(username="Ferdinand", email="ferdinand@example.com", password="test123", role=User.Role.ADMIN)

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
