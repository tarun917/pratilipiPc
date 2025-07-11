from django.contrib import admin
from .models import NotificationModel

@admin.register(NotificationModel)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'timestamp', 'related_tab')