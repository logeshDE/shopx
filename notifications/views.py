from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import Notification


@login_required
def notification_list(request):
    all_notifs = Notification.objects.filter(user=request.user)

    # Optional type filter
    type_filter = request.GET.get('type', '')
    if type_filter:
        all_notifs = all_notifs.filter(type=type_filter)

    paginator = Paginator(all_notifs, 20)
    page      = paginator.get_page(request.GET.get('page', 1))

    # Mark all visible ones as read
    all_notifs.filter(is_read=False).update(is_read=True)

    return render(request, 'notifications/notification_list.html', {
        'notifications':   page,
        'type_filter':     type_filter,
        'type_choices':    Notification.TYPE_CHOICES,
    })


@login_required
@require_POST
def mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return JsonResponse({'success': True})


@login_required
@require_POST
def mark_all_read(request):
    count = Notification.objects.filter(
        user=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({'success': True, 'marked': count})


@login_required
@require_POST
def delete_notification(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.delete()
    return JsonResponse({'success': True})