import django_filters
from .models import Request

# specific filter for request model
class RequestFilter(django_filters.FilterSet):
    class Meta:
        model = Request
        fields = ["status", "category", "department"]