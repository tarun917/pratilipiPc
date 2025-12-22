from django.db import models
from django.utils import timezone
from profileDesk.models import CustomUser


class NotificationModel(models.Model):
    class RelatedTab(models.TextChoices):
        HOME = "home", "Home"
        COMMUNITY = "community", "Community"
        STORE = "store", "Store"

    class NotificationType(models.TextChoices):
        DIGITAL_LAUNCH = "digital_launch", "Digital Comic Launch"
        DIGITAL_EPISODE = "digital_episode", "Digital Comic Episode"
        MOTION_LAUNCH = "motion_launch", "Motion Comic Launch"
        MOTION_EPISODE = "motion_episode", "Motion Comic Episode"
        ADMIN = "admin", "Admin Broadcast"

    class ComicType(models.TextChoices):
        DIGITAL = "digital", "Digital"
        MOTION = "motion", "Motion"

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications")
    notification_type = models.CharField(max_length=32, choices=NotificationType.choices)
    related_tab = models.CharField(max_length=16, choices=RelatedTab.choices, default=RelatedTab.HOME)
    comic_type = models.CharField(max_length=16, choices=ComicType.choices, null=True, blank=True)

    title = models.CharField(max_length=200)
    message = models.TextField()
    image_url = models.URLField(blank=True, null=True)
    deeplink = models.CharField(max_length=300, blank=True, null=True)

    comic_id = models.CharField(max_length=100, blank=True, null=True)
    episode_id = models.CharField(max_length=100, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    ttl = models.PositiveIntegerField(default=172800)
    collapse_key = models.CharField(max_length=100, blank=True, null=True)
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True)

    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "read_at", "-created_at"]),
            models.Index(fields=["notification_type", "-created_at"]),
            models.Index(fields=["comic_type", "comic_id"]),
            models.Index(fields=["related_tab", "-created_at"]),
        ]
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"

    def __str__(self) -> str:
        base = f"{self.title or self.message[:30]}"
        audience = self.user.username if self.user_id else "broadcast"
        return f"{audience} · {self.notification_type} · {base}"

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self):
        if not self.read_at:
            self.read_at = timezone.now()
            self.save(update_fields=["read_at"])


class DeviceToken(models.Model):
    class Platform(models.TextChoices):
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"
        WEB = "web", "Web"

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="device_tokens")
    token = models.CharField(max_length=255, unique=True)
    platform = models.CharField(max_length=16, choices=Platform.choices)
    app_version = models.CharField(max_length=32, blank=True, null=True)
    locale = models.CharField(max_length=16, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "platform"]),
            models.Index(fields=["is_active", "platform"]),
        ]
        verbose_name = "Device Token"
        verbose_name_plural = "Device Tokens"

    def __str__(self) -> str:
        return f"{self.user_id} · {self.platform} · {self.token[:8]}..."