from .models import Request, RequestHistory
from django.db import transaction

class InvalidStatusTransition(Exception):
    ...


def change_request_status(request_obj, new_status, changed_by):
        allowed_transitions = { 
            Request.Status.PENDING : Request.Status.IN_REVIEW,
            Request.Status.IN_REVIEW: Request.Status.IN_PROGRESS,
            Request.Status.IN_PROGRESS: Request.Status.RESOLVED
        }

        old_status = request_obj.status
        next_status = allowed_transitions.get(old_status)

        if new_status != next_status:
            raise InvalidStatusTransition("Invalid status transition")

        request_obj.status = next_status
        with transaction.atomic():
            request_obj.save()
            RequestHistory.objects.create(request = request_obj, old_status = old_status, new_status = next_status, changed_by = changed_by)