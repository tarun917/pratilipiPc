from django.conf import settings
from django.db import models


class ReadingActivity(models.Model):
    TYPE_CHOICES = (
        ("digital", "Digital"),
        ("motion", "Motion"),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reading_activity",
    )
    type = models.CharField(max_length=16, choices=TYPE_CHOICES)

    # Use string IDs to support both UUID (digital) and int (motion)
    comic_id = models.CharField(max_length=64)
    episode_id = models.CharField(max_length=64, null=True, blank=True)

    progress_percent = models.FloatField(default=0.0)
    position_ms = models.IntegerField(null=True, blank=True)

    comic_title = models.CharField(max_length=255, blank=True, default="")
    episode_label = models.CharField(max_length=255, blank=True, default="")
    cover_url = models.URLField(blank=True, default="")

    last_read_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    snoozed_until = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = (("user", "type", "comic_id"),)
        indexes = [
            models.Index(fields=["user", "-last_read_at"]),
            models.Index(fields=["user", "-finished_at"]),
            models.Index(fields=["user", "type", "comic_id"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.type}:{self.comic_id}"