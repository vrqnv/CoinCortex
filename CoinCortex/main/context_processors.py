from .models import Notification


def unread_notifications(request):
    """Context processor для непрочитанных уведомлений"""
    if request.user.is_authenticated:
        return {
            'unread_notifications': Notification.objects.filter(
                user=request.user, read=False
            ).count()
        }
    return {'unread_notifications': 0}

