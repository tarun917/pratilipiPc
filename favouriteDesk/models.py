from django.db import models
from profileDesk.models import CustomUser


class FavouriteModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic_type = models.CharField(
        max_length=10,
        choices=[('digital', 'Digital'), ('motion', 'Motion')]
    )
    # Store as string to support UUID (digital) and numeric (motion)
    comic_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comic_type', 'comic_id')
        indexes = [
            models.Index(fields=['user', 'comic_type', 'comic_id']),
            models.Index(fields=['comic_type', 'comic_id']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.comic_type} Comic {self.comic_id}"