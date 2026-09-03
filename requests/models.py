from django.db import models
from django.conf import settings
from categories.models import Category
from departments.models import Department
# Create your models here.

class Request(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_REVIEW = "IN_REVIEW", "In Review"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"

    title = models.CharField(max_length=100)
    description = models.TextField()
    location = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    department = models.ForeignKey(Department, on_delete=models.PROTECT)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class RequestHistory(models.Model):
    # mudar para cascade no futuro se ao apagar a request quiser que o histórico seja apagado junto
    request = models.ForeignKey(Request, on_delete=models.PROTECT)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    old_status = models.CharField(max_length=20, choices=Request.Status.choices)
    new_status = models.CharField(max_length=20, choices=Request.Status.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.request} - {self.old_status} -> {self.new_status}"