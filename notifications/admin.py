from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display   = ['user', 'type', 'title', 'is_read', 'created_at']
    list_filter    = ['type', 'is_read', 'created_at']
    search_fields  = ['user__email', 'title', 'message']
    list_editable  = ['is_read']
    readonly_fields = ['created_at']
    raw_id_fields  = ['user']