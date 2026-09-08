from requests.models import Notification


def unread_notifications(request):
    base_context = {'unread_notifications_count': 0, 'latest_notification': None}

    if not request.user.is_authenticated:
        return base_context

    unread = Notification.objects.filter(recipient=request.user, is_read=False)
    latest = unread.order_by('-created_at').first()
    unread_count = unread.count()

    toast_shown = request.session.get('toast_shown', False)
    show_after_login = request.session.get('show_notification_after_login', False)
    force_show = request.GET.get('show_notification') == '1'

    if latest and not toast_shown and (show_after_login or force_show):
        request.session['toast_shown'] = True
        request.session['show_notification_after_login'] = False
        return {
            'unread_notifications_count': unread_count,
            'latest_notification': latest,
        }

    return {
        'unread_notifications_count': unread_count,
        'latest_notification': None,
    }
