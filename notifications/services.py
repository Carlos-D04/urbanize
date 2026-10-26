from datetime import timedelta

from .models import Notification, EmailDelivery
from reports.models import Request

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
    if new_status == Request.Status.IN_PROGRESS or new_status == Request.Status.RESOLVED:
        create_email_delivery(notification_obj)

    return notification_obj


def reclassified_warning(request_obj, old_category, new_category, new_department, old_department):
    message = (
    f'Your solicitation "{request_obj.title}" has been reclassified '
    f'from "{old_category.name}" to "{new_category.name}". '
    f'The responsible department now is "{new_department.name}".'
    )

    notification_obj = Notification.objects.create(recipient = request_obj.author, request = request_obj, notification_type = Notification.NotificationType.RECLASSIFIED, title = "Solicitation reclassified", message = message, new_department = new_department, old_department = old_department, old_category = old_category, new_category = new_category)

    create_email_delivery(notification_obj)

    return notification_obj

def create_email_delivery(notification_obj):

    delivery = EmailDelivery.objects.create(notification = notification_obj)

    return delivery

def can_attempt_email_delivery(delivery, now):

    if delivery.status == EmailDelivery.StatusType.SENT or delivery.attempts >= 3:
        return False

    if delivery.last_attempted_at:
        next_attempt_at = delivery.last_attempted_at + timedelta(minutes=30)

        if now < next_attempt_at:
            return False

    if EmailDelivery.objects.filter(notification__recipient = delivery.notification.recipient, status = EmailDelivery.StatusType.SENT, sent_at__gt = (now - timedelta(minutes = 30))).exists():
        return False

    return True
