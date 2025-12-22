from django.contrib import admin
from django.utils.html import format_html
from .models import NotificationModel, DeviceToken


@admin.register(NotificationModel)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "notification_type",
        "related_tab",
        "user",
        "comic_type",
        "comic_id",
        "episode_id",
        "is_read_admin",
        "created_at",
    )
    list_filter = ("notification_type", "related_tab", "comic_type", "created_at")
    search_fields = ("title", "message", "user__username", "comic_id", "episode_id", "collapse_key", "idempotency_key")
    readonly_fields = ("created_at", "read_at")
    ordering = ("-created_at",)

    def is_read_admin(self, obj: NotificationModel):
        return format_html("<b style='color:{}'>{}</b>", "green" if obj.is_read else "red", "Yes" if obj.is_read else "No")

    is_read_admin.short_description = "Read"


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "token_short", "is_active", "last_seen_at", "created_at")
    list_filter = ("platform", "is_active", "created_at")
    search_fields = ("user__username", "token", "app_version", "locale")
    readonly_fields = ("created_at", "last_seen_at")
    ordering = ("-last_seen_at",)

    def token_short(self, obj: DeviceToken):
        return obj.token[:12] + "..."
    token_short.short_description = "Token"