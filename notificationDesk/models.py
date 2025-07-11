from django.db import models
from profileDesk.models import CustomUser

class NotificationModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    related_tab = models.CharField(max_length=50, choices=[('home', 'Home'), ('community', 'Community')])

    def __str__(self):
        return f"{self.user.username} - {self.message}"