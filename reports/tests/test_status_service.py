
from reports.models import Request, RequestHistory
from reports.services import InvalidStatusTransition, change_request_status
from .base import RequestTestCase


class StatusServiceTests(RequestTestCase):
    def test_service_rejects_skipped_status(self):

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
