from django.db import models

from accounts.models import User
from reports.models import Request
from categories.models import Category
from departments.models import Department


# Create your models here.

# I'm probably changing notifications to be event-driven with rabbitmq just for the sake of it.(later tho)
class Notification (models.Model):
    class NotificationType(models.TextChoices):
        STATUS_CHANGED = "STATUS_CHANGED", "Status Changed"
        RECLASSIFIED = "RECLASSIFIED", "Reclassified"
        NEW_MESSAGE = "NEW_MESSAGE", "New Message"

    recipient = models.ForeignKey(User, on_delete=models.PROTECT, related_name="notifications") 
    # for now, every notification comes from a request so its mandatory to have it. Later i'll change it so it's not required when sending a notification
    request = models.ForeignKey(Request, on_delete=models.PROTECT, related_name="notifcations") 
    type = models.CharField(max_length=30, choices=NotificationType.choices)
    title = models.CharField(max_length=100)
    message = models.TextField()
    old_status = models.CharField(max_length=20, null=True, blank=True)
    new_status = models.CharField(max_length=20, null=True, blank=True)
    old_category = models.ForeignKey(Category, on_delete = models.PROTECT, null = True, blank = True, related_name = "old_category_notifications")
    new_category = models.ForeignKey(Category, on_delete = models.PROTECT, null = True, blank = True, related_name = "new_category_notifications")
    old_department = models.ForeignKey(Department, on_delete = models.PROTECT, null = True, blank = True, related_name = "old_department_notifications")
    new_department = models.ForeignKey(Department, on_delete = models.PROTECT, null = True, blank = True, related_name = "new_department_notifications")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)