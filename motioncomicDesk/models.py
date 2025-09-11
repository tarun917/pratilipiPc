from django.db import models
from profileDesk.models import CustomUser


class ComicModel(models.Model):
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100)
    cover_image = models.ImageField(upload_to='motioncomics/covers/', null=True, blank=True)
    description = models.TextField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    view_count = models.IntegerField(default=0)
    favourite_count = models.IntegerField(default=0)
    rating_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.title


class EpisodeModel(models.Model):
    comic = models.ForeignKey(ComicModel, on_delete=models.CASCADE)
    episode_number = models.PositiveIntegerField()
    thumbnail = models.ImageField(upload_to='motioncomics/episodes/', null=True, blank=True)

    # Playback sources
    video_url = models.URLField(blank=True, null=True)  # Optional direct URL
    video_file = models.FileField(
        upload_to='motioncomics/episodes/', blank=True, null=True,
        help_text="Upload MP4 video for this episode (optional)"
    )

    # Pricing/locks
    is_free = models.BooleanField(default=False)
    coin_cost = models.IntegerField(default=50)

    # Admin lock only (compat): per-user access is tracked via EpisodeAccess
    is_locked = models.BooleanField(default=True)

    short_description = models.TextField(max_length=200)

    class Meta:
        unique_together = ('comic', 'episode_number')
        indexes = [
            models.Index(fields=['comic', 'episode_number']),
        ]
        ordering = ['episode_number']

    def __str__(self):
        return f"{self.comic.title} - Episode {self.episode_number}"


class CommentModel(models.Model):
    episode = models.ForeignKey(EpisodeModel, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='motion_comments')
    comment_text = models.TextField(max_length=256)
    likes_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.comment_text}"


class EpisodeAccess(models.Model):
    SOURCE_COINS = 'COINS'
    SOURCE_PREMIUM = 'PREMIUM'
    SOURCE_GRANT = 'GRANT'
    SOURCE_CHOICES = [
        (SOURCE_COINS, 'Coins'),
        (SOURCE_PREMIUM, 'Premium'),
        (SOURCE_GRANT, 'Grant'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='motion_episode_accesses')
    episode = models.ForeignKey(EpisodeModel, on_delete=models.CASCADE, related_name='accesses')
    source = models.CharField(max_length=16, choices=SOURCE_CHOICES, default=SOURCE_COINS)
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'episode')
        indexes = [
            models.Index(fields=['user', 'episode']),
        ]

    def __str__(self):
        return f"{self.user.username} unlocked {self.episode} via {self.source}"