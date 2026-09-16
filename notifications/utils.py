from .models import Notification


def create_notification(user, type, title, message, link=''):
    """
    Creates an in-app notification record.
    Always synchronous — call from signals and views directly.
    Email dispatch happens separately via Celery tasks.
    """
    if user is None:
        return None
    return Notification.objects.create(
        user    = user,
        type    = type,
        title   = title,
        message = message,
        link    = link,
    )