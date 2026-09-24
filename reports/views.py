from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.mixins import CreateModelMixin, RetrieveModelMixin,UpdateModelMixin,ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework import status
from rest_framework.permissions import SAFE_METHODS

from .filters import RequestFilter 
from .models import Request, RequestHistory
from .serializers import RequestSerializer, RequestStatusSerializer, RequestHistorySerializer, RequestCategorySerializer
from .permissions import RequestPermission, StatusPermission
from .services import change_request_status, change_classified, InvalidStatusTransition, InvalidCategoryChange

# Create your views here.

class RequestViewSet(CreateModelMixin, RetrieveModelMixin,UpdateModelMixin,ListModelMixin, GenericViewSet):
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

    @action(detail=True, methods=["patch"], url_path="reclassify", permission_classes=[IsAuthenticated, StatusPermission])
    def reclassify(self, request, pk=None):
        request_obj = self.get_object()

        serializer = RequestCategorySerializer(data = request.data)
        serializer.is_valid(raise_exception=True)

        old_category = request_obj.category
        new_category = serializer.validated_data["category"]
        old_department = request_obj.department
        new_department = new_category.department

        try:
            change_classified(request_obj, new_category = new_category, changed_by = request.user)
        except InvalidCategoryChange:
            return Response({"detail": "You cannot change a category to the same category"}, status = status.HTTP_400_BAD_REQUEST)

        return Response({"detail": f"Your old category({old_category.name}) from {old_department.name} has been changed to {new_category.name} on {new_department.name}"}, status.HTTP_200_OK)