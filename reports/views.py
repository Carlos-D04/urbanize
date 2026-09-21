from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from rest_framework.permissions import SAFE_METHODS

from .filters import RequestFilter 
from .models import Request, RequestHistory
from .serializers import RequestSerializer, RequestStatusSerializer, RequestHistorySerializer
from .permissions import RequestPermission, StatusPermission
from .services import change_request_status, InvalidStatusTransition

# Create your views here.

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer
    permission_classes = [IsAuthenticated, RequestPermission]
    filterset_class = RequestFilter
    search_fields = ["title", "description"]
    ordering_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

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
        
        request_obj = self.get_object() # gets the PK from URL

        try:
            change_request_status(request_obj, new_status = serializer.validated_data["status"], changed_by = request.user)

        except InvalidStatusTransition:
            return Response({"detail": "Invalid status transition"}, status = status.HTTP_400_BAD_REQUEST)


        return Response({"detail": "Status updated successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="history", permission_classes = [IsAuthenticated, RequestPermission])
    def check_history(self, request, pk=None):
        request_obj = self.get_object()

        queryset = RequestHistory.objects.filter(request = request_obj)

        serializer = RequestHistorySerializer(queryset, many = True)

        return Response(serializer.data) 
