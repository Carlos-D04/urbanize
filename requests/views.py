from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .models import Request
from .serializers import RequestSerializer

# Create your views here.

class RequestViewSet(viewsets.ModelViewSet):
    queryset = Request.objects.all()
    serializer_class = RequestSerializer

    permission_classes = [IsAuthenticated]

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