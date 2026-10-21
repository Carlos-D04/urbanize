from rest_framework import status

from reports.models import Request
from .base import RequestTestCase


class RequestFiltersTests(RequestTestCase):
    def test_citizen_can_filter_own_requests_by_status(self):
        self.client.force_authenticate(user=self.citizen)

        resolved_request = Request.objects.create(
            author=self.citizen,
            category=self.category,
            department=self.department,
            title="Resolved request",
            description="This request has already been resolved",
            location="Aracaju",
            status=Request.Status.RESOLVED
        )

        response = self.client.get(f"/requests/?status=RESOLVED")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request_ids = [request["id"] for request in response.data["results"]]

        self.assertIn(resolved_request.id, request_ids)
        self.assertNotIn(self.citizen_request.id, request_ids)

    def test_citizen_can_search_own_requests_by_text(self):
        self.client.force_authenticate(user=self.citizen)

        searched_request = Request.objects.create(
            author=self.citizen,
            category=self.category,
            department=self.department,
            title="Buraco na avenida",
            description="Problema grave na via",
            location="Aracaju"
        )

        response = self.client.get("/requests/?search=buraco")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request_ids = [request["id"] for request in response.data["results"]]

        self.assertIn(searched_request.id, request_ids)
        self.assertNotIn(self.citizen_request.id, request_ids)

    def test_citizen_can_search_requests_by_description(self):
        self.client.force_authenticate(user=self.citizen)

        searched_request = Request.objects.create(
            author=self.citizen,
            category=self.category,
            department=self.department,
            title="Problema na rua",
            description="Existe um buraco enorme na pista",
            location="Aracaju"
        )

        response = self.client.get("/requests/?search=buraco")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request_ids = [request["id"]for request in response.data["results"]]

        self.assertIn(searched_request.id, request_ids)

    def test_search_does_not_return_another_citizen_request(self):
        self.client.force_authenticate(user=self.citizen)

        other_request = Request.objects.create(
            author=self.other_citizen,
            category=self.category,
            department=self.department,
            title="Buraco na avenida",
            description="Problema grave na via",
            location="Aracaju"
        )

        response = self.client.get("/requests/?search=buraco")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request_ids = [request["id"]for request in response.data["results"]]

        self.assertNotIn(other_request.id, request_ids)

    def test_citizen_can_filter_own_requests_by_category(self):
        self.client.force_authenticate(user=self.citizen)

        category_request = Request.objects.create(
            author=self.citizen,
            category=self.other_category,
            department=self.other_department,
            title="Broken street light",
            description="Street light problem",
            location="Aracaju"
        )

        response = self.client.get(f"/requests/?category={self.other_category.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request_ids = [request["id"] for request in response.data["results"]]

        self.assertIn(category_request.id, request_ids)
        self.assertNotIn(self.citizen_request.id, request_ids)

    def test_staff_can_filter_requests_by_department(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(f"/requests/?department={self.citizen_request.department.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        request_id = [request["id"] for request in response.data["results"]]

        self.assertIn(self.citizen_request.id, request_id)
        self.assertNotIn(self.other_citizen_request2.id, request_id)
