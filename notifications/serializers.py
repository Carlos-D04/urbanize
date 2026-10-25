from .models import Notification
from rest_framework import serializers

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ['id', 'request', 'notification_type', 'title', 'message', 'old_status', 'new_status', 'old_category', 'new_category', 'old_department', 'new_department', 'is_read', 'created_at']
        read_only_fields = ['id', 'request', 'notification_type', 'title', 'message', 'old_status', 'new_status', 'old_category', 'new_category', 'old_department', 'new_department', 'is_read', 'created_at']