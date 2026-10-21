
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


def reclassified_warning(request_obj, old_category, new_category, new_department, old_department):
    message = (
    f'Your solicitation "{request_obj.title}" has been reclassified '
    f'from "{old_category.name}" to "{new_category.name}". '
    f'The responsible department now is "{new_department.name}".'
    )

    notification_obj = Notification.objects.create(recipient = request_obj.author, request = request_obj, notification_type = Notification.NotificationType.RECLASSIFIED, title = "Solicitation reclassified", message = message, new_department = new_department, old_department = old_department, old_category = old_category, new_category = new_category)

    return notification_obj