from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class PerformanceTestCase(APITestCase):

    def setUp(self):
        self.citizen = User.objects.create_user(
            username="carlos",
            password="test123",
            role=User.Role.CITIZEN
        )

    def test_setup_only(self):
        pass
