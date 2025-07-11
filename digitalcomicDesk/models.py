import uuid
from django.db import models
from profileDesk.models import CustomUser

class ComicModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=100)
    cover_image = models.ImageField(upload_to='digitalcomics/covers/', null=True, blank=True)
    description = models.TextField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)
    view_count = models.IntegerField(default=0)
    favourite_count = models.IntegerField(default=0)
    rating_count = models.PositiveIntegerField(default=0)  # Add this line
    is_creator_comic = models.BooleanField(default=False)

    def __str__(self):
        return self.title
    

class EpisodeModel(models.Model):
    comic = models.ForeignKey(ComicModel, on_delete=models.CASCADE)
    episode_number = models.PositiveIntegerField()
    thumbnail = models.ImageField(upload_to='digitalcomics/episodes/', null=True, blank=True)
    content_url = models.URLField()
    is_free = models.BooleanField(default=False)
    coin_cost = models.IntegerField(default=50)
    is_locked = models.BooleanField(default=True)

    class Meta:
        unique_together = ('comic', 'episode_number')  # Add this to prevent duplicates

    def __str__(self):
        return f"{self.comic.title} - Episode {self.episode_number}"

class CommentModel(models.Model):
    episode = models.ForeignKey(EpisodeModel, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='digital_comments')
    comment_text = models.TextField(max_length=256)
    likes_count = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.comment_text}"