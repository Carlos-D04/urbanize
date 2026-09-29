
from .models import Notification

def create_status_notification(request_obj, recipient, notification_type, title, old_status, new_status, message):

    notification_obj = Notification.objects.create(
        request = request_obj, 
        recipient = recipient, 
        notification_type = notification_type, 
        old_status = old_status, 
        new_status = new_status, 
        title = title, 
        message = message
    )

    return notification_obj