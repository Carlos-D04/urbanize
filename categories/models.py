from django.db import models
from departments.models import Department
# Create your models here.

class Category(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True
        )
    description = models.TextField()
    department = models.ForeignKey(Department, on_delete=models.PROTECT)

    def __str__(self):
        return self.name