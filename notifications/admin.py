from django.contrib import admin
from notifications.models import Notification

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'sent', 'created_at')
    list_filter = ('sent', 'created_at')
    search_fields = ('user__username', 'message')
