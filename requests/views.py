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