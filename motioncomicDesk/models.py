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
    video_url = models.URLField(blank=True, null=True)  # Optional direct URL
    video_file = models.FileField(
        upload_to='motioncomics/episodes/', blank=True, null=True,
        help_text="Upload MP4 video for this episode (optional)"
    )
    is_free = models.BooleanField(default=False)
    coin_cost = models.IntegerField(default=50)
    # Keep this field for backward compatibility in admin and existing clients,
    # but per-user lock will be computed via UserEpisodeUnlock below.
    is_locked = models.BooleanField(default=True)
    short_description = models.TextField(max_length=200)

    class Meta:
        unique_together = ('comic', 'episode_number')

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


class UserEpisodeUnlock(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='motion_unlocks')
    episode = models.ForeignKey(EpisodeModel, on_delete=models.CASCADE, related_name='unlocks')
    unlocked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'episode')

    def __str__(self):
        return f"{self.user.username} unlocked {self.episode}"