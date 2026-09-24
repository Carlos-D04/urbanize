from .models import Request, RequestHistory
from django.db import transaction

class InvalidStatusTransition(Exception):
    ...

class InvalidCategoryChange(Exception):
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
            RequestHistory.objects.create(request = request_obj, old_status = old_status, new_status = next_status, changed_by = changed_by, event_type = RequestHistory.EventType.STATUS_CHANGED)

def change_classified(request_obj, new_category, changed_by):

    old_category = request_obj.category
    old_department = request_obj.department
    new_department = new_category.department

    if new_category == old_category:
          raise InvalidCategoryChange("You cannot change a category to the same category")

    with transaction.atomic():
        request_obj.category = new_category
        request_obj.department = new_department
        request_obj.save()
        RequestHistory.objects.create(request = request_obj, changed_by = changed_by, old_category = old_category, old_department = old_department, new_category = new_category, new_department = new_department, event_type = RequestHistory.EventType.RECLASSIFIED)
        
    

    

     