from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import SAFE_METHODS

from .models import Request, RequestHistory
from .serializers import RequestSerializer, RequestStatusSerializer, RequestHistorySerializer
from .permissions import RequestPermission, StatusPermission

# Create your views here.

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    permission_classes = [IsAuthenticated, RequestPermission]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        user = self.request.user
        if user.role == user.Role.CITIZEN:
            return Request.objects.filter(author = user)
        if user.role == user.Role.STAFF:
            return Request.objects.filter(department = user.department)
        if user.role == user.Role.ADMIN:
            return Request.objects.all()
        return Request.objects.none()

    # action here just because i dont want status to be a field that can be changed in any type of request.
    @action(detail = True, methods=["patch"], url_path="change-status", permission_classes = [IsAuthenticated, StatusPermission])
    def change_status(self, request, pk=None):
        serializer = RequestStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # order of the next status transitions allowed.
        allowed_transitions = { 
            Request.Status.PENDING : Request.Status.IN_REVIEW,
            Request.Status.IN_REVIEW: Request.Status.IN_PROGRESS,
            Request.Status.IN_PROGRESS: Request.Status.RESOLVED
        }
        
        request_obj = self.get_object() #ID from URL

        old_status = request_obj.status
        new_status = serializer.validated_data["status"]
        next_status = allowed_transitions.get(old_status)

        if new_status != next_status:
            return Response({"detail": "Invalid status transition"}, status=status.HTTP_400_BAD_REQUEST)

        request_obj.status = next_status
        with transaction.atomic():
            request_obj.save()
            RequestHistory.objects.create(request = request_obj, old_status = old_status, new_status = next_status, changed_by = request.user)

        return Response({"detail": "Status updated successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="history", permission_classes = [IsAuthenticated, RequestPermission])
    def check_history(self, request, pk=None):
        request_obj = self.get_object()

        queryset = RequestHistory.objects.filter(request = request_obj)

        serializer = RequestHistorySerializer(queryset, many = True)

        return Response(serializer.data) 
