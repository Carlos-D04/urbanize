from django.contrib.auth import get_user_model

from rest_framework import status
from rest_framework.test import APITestCase
from unittest.mock import patch

from departments.models import Department
from categories.models import Category
from .models import Request, RequestHistory
from .services import InvalidStatusTransition, InvalidCategoryChange, change_request_status, change_classified

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

    def test_request_without_history_returns_empty_list(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(f"/requests/{self.other_citizen_request.id}/history/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data), 0)

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

    def test_idk(self): # Service Test

        old_status = self.citizen_request.status

        with self.assertRaises(InvalidStatusTransition):
            change_request_status(self.citizen_request, new_status = Request.Status.IN_PROGRESS, changed_by = self.staff)

        self.citizen_request.refresh_from_db()
        
        self.assertEqual(old_status, self.citizen_request.status)

    def test_service_changes_request_status(self):

        self.assertEqual(RequestHistory.objects.count(), 0)

        change_request_status(self.citizen_request, Request.Status.IN_REVIEW, changed_by = self.staff)

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.status, Request.Status.IN_REVIEW)

        self.assertEqual(RequestHistory.objects.count(), 1)
        history = RequestHistory.objects.get(request = self.citizen_request)

        self.assertEqual(history.request, self.citizen_request)
        self.assertEqual(history.changed_by, self.staff)
        self.assertEqual(history.old_status, Request.Status.PENDING)
        self.assertEqual(history.new_status, Request.Status.IN_REVIEW)

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

    def test_staff_can_change_category(self):
        self.client.force_authenticate(user=self.staff)

        data = {
            "category": self.other_category.id
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.citizen_request.refresh_from_db()

        self.assertEqual(
            self.citizen_request.category,
            self.other_category
        )


    def test_admin_can_change_category(self):
        self.client.force_authenticate(user=self.admin)

        data = {
            "category": self.other_category.id
        }

        response = self.client.patch(
            f"/requests/{self.citizen_request.id}/",
            data=data,
            format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.citizen_request.refresh_from_db()

        self.assertEqual(
            self.citizen_request.category,
            self.other_category
        )


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
    def test_service_reclassifies_request(self):
        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)
        self.assertEqual(RequestHistory.objects.count(), 0)

        change_classified(
            self.citizen_request,
            self.other_category,
            self.staff
        )

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.other_category)
        self.assertEqual(self.citizen_request.department, self.other_department)

        self.assertEqual(RequestHistory.objects.count(), 1)

        history = RequestHistory.objects.get(request=self.citizen_request)

        self.assertEqual(history.event_type, RequestHistory.EventType.RECLASSIFIED)
        self.assertEqual(history.changed_by, self.staff)
        self.assertEqual(history.old_category, self.category)
        self.assertEqual(history.new_category, self.other_category)
        self.assertEqual(history.old_department, self.department)
        self.assertEqual(history.new_department, self.other_department)


    def test_service_rejects_same_category(self):
        self.assertEqual(RequestHistory.objects.count(), 0)

        with self.assertRaises(InvalidCategoryChange):
            change_classified(
                self.citizen_request,
                self.category,
                self.staff
            )

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)

        self.assertEqual(RequestHistory.objects.count(), 0)


    def test_reclassification_rolls_back_if_history_creation_fails(self):
        with self.assertRaises(Exception):
            with patch(
                "reports.services.RequestHistory.objects.create",
                side_effect=Exception("Simulated error")
            ):
                change_classified(
                    self.citizen_request,
                    self.other_category,
                    self.staff
                )

        self.citizen_request.refresh_from_db()

        self.assertEqual(self.citizen_request.category, self.category)
        self.assertEqual(self.citizen_request.department, self.department)

        self.assertEqual(RequestHistory.objects.count(), 0)

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
class PerformanceTestCase(APITestCase):

    def setUp(self):
        self.citizen = User.objects.create_user(
            username="carlos",
            password="test123",
            role=User.Role.CITIZEN
        )

    def test_setup_only(self):
        pass