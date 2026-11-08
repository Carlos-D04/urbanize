from rest_framework.permissions import BasePermission, SAFE_METHODS

class RequestPermission(BasePermission):

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        
        if request.user.role == request.user.Role.CITIZEN:
            return obj.author == request.user and obj.status == obj.Status.PENDING
        
        if request.user.role == request.user.Role.STAFF:
            return obj.department == request.user.department

        if request.user.role == request.user.Role.ADMIN:
            return True

        return False

def can_manage_request(user, request_obj):
    return user.role == user.Role.ADMIN or (
        user.role == user.Role.STAFF
        and user.department_id == request_obj.department_id
    )


class StatusPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return can_manage_request(request.user, obj)
