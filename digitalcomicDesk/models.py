import uuid
from django.db import models
from django.utils import timezone
from profileDesk.models import CustomUser


def slice_upload_path(instance, filename):
    # Store under: digitalcomics/episodes/<episode_uuid>/slices/<filename>
    # Admin import will standardize filenames (e.g., 0001.jpg, 0002.jpg ...)
    return f"digitalcomics/episodes/{instance.episode_id}/slices/{filename}"


class ComicModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100)
    cover_image = models.ImageField(upload_to='digitalcomics/covers/', null=True, blank=True)
    description = models.TextField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    view_count = models.IntegerField(default=0)
    favourite_count = models.IntegerField(default=0)
    rating_count = models.PositiveIntegerField(default=0)
    is_creator_comic = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Digital Comic"
        verbose_name_plural = "Digital Comics"
        indexes = [
            models.Index(fields=["genre"]),
        ]

    def __str__(self):
        return self.title


class EpisodeModel(models.Model):
    comic = models.ForeignKey('ComicModel', on_delete=models.CASCADE, related_name='episodes')
    episode_number = models.PositiveIntegerField()
    thumbnail = models.ImageField(upload_to='digitalcomics/episodes/', null=True, blank=True)

    # Optional PDF or external URL; image-slice pipeline uses SliceModel
    content_url = models.URLField(blank=True, null=True)
    content_file = models.FileField(
        upload_to='digitalcomics/episodes/', blank=True, null=True,
        help_text="Upload PDF file for this episode (optional)"
    )

    is_free = models.BooleanField(default=False)
    coin_cost = models.IntegerField(default=50)
    # Admin-configured lock. Do NOT flip globally on user unlock; use EpisodeAccess.
    is_locked = models.BooleanField(default=True)

    # End-of-episode engagement counters (denormalized)
    likes_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)
    comments_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ('comic', 'episode_number')
        ordering = ['episode_number']
        indexes = [
            models.Index(fields=['comic', 'episode_number']),
            models.Index(fields=['is_locked']),
            models.Index(fields=['is_free']),
        ]
        verbose_name = "Episode"
        verbose_name_plural = "Episodes"

    def __str__(self):
        try:
            return f"{self.comic} - Episode {self.episode_number}"
        except ComicModel.DoesNotExist:
            return f"Missing Comic - Episode {self.id}"

    def get_next_episode(self):
        """
        Returns the next episode within the same comic by episode_number+1, or None.
        """
        return EpisodeModel.objects.filter(
            comic=self.comic,
            episode_number=self.episode_number + 1
        ).first()


class SliceModel(models.Model):
    """
    Represents a single JPEG slice of an episode for continuous vertical reading.
    Order starts from 1 and increases without gaps ideally.
    Height is optional; when provided, clients can pre-size items for better UX.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(EpisodeModel, on_delete=models.CASCADE, related_name='slices')
    order = models.PositiveIntegerField(help_text="1-based sequential order within the episode")
    file = models.ImageField(upload_to=slice_upload_path)
    width = models.PositiveIntegerField(default=1080, help_text="Pixel width, e.g., 1080")
    height = models.PositiveIntegerField(null=True, blank=True, help_text="Pixel height if known")

    class Meta:
        unique_together = ('episode', 'order')
        ordering = ['episode', 'order']
        indexes = [
            models.Index(fields=['episode', 'order']),
        ]
        verbose_name = "Slice"
        verbose_name_plural = "Slices"

    def __str__(self):
        return f"{self.episode} - Slice {self.order}"


class EpisodeAccess(models.Model):
    """
    Per-user access record for an episode (unlocked via coins or premium).
    This is the source of truth for whether a specific user can read a locked episode.
    Do NOT mutate EpisodeModel.is_locked on unlock; it represents admin lock intent.
    """
    SOURCE_COINS = 'coins'
    SOURCE_PREMIUM = 'premium'
    SOURCE_CHOICES = [
        (SOURCE_COINS, 'Coins'),
        (SOURCE_PREMIUM, 'Premium'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='digital_episode_access')
    episode = models.ForeignKey(EpisodeModel, on_delete=models.CASCADE, related_name='access_records')
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES)
    unlocked_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'episode')
        ordering = ['-unlocked_at']
        indexes = [
            models.Index(fields=['user', 'episode']),
            models.Index(fields=['episode']),
        ]
        verbose_name = "Episode Access"
        verbose_name_plural = "Episode Access"

    def __str__(self):
        return f"{self.user.username} -> {self.episode} ({self.source})"


class CommentModel(models.Model):
    """
    Threaded comments for an episode.
    Top-level comments have parent=None.
    Replies point to a parent comment (same episode).
    """
    id = models.BigAutoField(primary_key=True)
    episode = models.ForeignKey(EpisodeModel, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='digital_comments')
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies',
        help_text="Parent comment for threaded replies (null for top-level)"
    )
    comment_text = models.TextField(max_length=256)
    likes_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['episode']),
            models.Index(fields=['user']),
            models.Index(fields=['parent']),
        ]
        verbose_name = "Comment"
        verbose_name_plural = "Comments"

    def __str__(self):
        return f"{self.user.username} - {self.comment_text}"