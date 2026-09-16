from .models import Notification


def notification_context(request):
    if not request.user.is_authenticated:
        return {'unread_notification_count': 0, 'latest_notifications': []}

    unread_count = Notification.objects.filter(
        user=request.user, is_read=False
    ).count()

    latest = Notification.objects.filter(
        user=request.user
    ).select_related('user')[:5]

    return {
        'unread_notification_count': unread_count,
        'latest_notifications':      latest,
    }