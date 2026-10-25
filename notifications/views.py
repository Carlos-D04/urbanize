from django.shortcuts import render
from rest_framework.mixins import ListModelMixin
from rest_framework.viewsets import GenericViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status

from .serializers import NotificationSerializer
from .models import Notification

# Create your views here.

class NotificationViewSet(ListModelMixin, GenericViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ["created_at"]
    ordering = ["-created_at", "-id"]

    def get_queryset(self):
        recipient = self.request.user

        return Notification.objects.filter(recipient = recipient)

    @action(detail=True, methods=["patch"], url_path="mark-read")
    def mark_as_read(self, request, pk = None):
        notification_obj = self.get_object()

        notification_obj.is_read = True
        notification_obj.save(update_fields=["is_read"])

        return Response({"detail": "Marked as read"}, status=status.HTTP_200_OK)
