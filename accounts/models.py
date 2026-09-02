from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):

    class Role(models.TextChoices):
        CITIZEN = "CITIZEN", "Citizen"
        STAFF = "STAFF", "Staff"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CITIZEN
        )


    
    department = models.ForeignKey(
        "departments.Department",
        on_delete=models.PROTECT,
        null=True,
        blank=True
        )
