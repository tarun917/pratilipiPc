from django.db import models
from profileDesk.models import CustomUser  # profileDesk se import

class Post(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField(max_length=512)
    image_url = models.ImageField(upload_to='posts/', null=True, blank=True)
    hashtags = models.JSONField(default=list)  # Array of hashtags
    commenting_enabled = models.BooleanField(default=True)
    share_count = models.IntegerField(default=0)  # Track shares
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Post by {self.user.username}"

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    text = models.TextField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post.id}"

class Poll(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    question = models.CharField(max_length=255)
    options = models.JSONField(default=dict)  # e.g., {"1": "Option 1", "2": "Option 2"}
    votes = models.JSONField(default=dict)  # e.g., {"1": 5, "2": 3"}
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Poll for Post {self.post.id}"

class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    option_id = models.CharField(max_length=10)  # Matches poll options key
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('poll', 'user')  # Ensure one vote per user per poll

    def __str__(self):
        return f"Vote by {self.user.username} on {self.poll.id}"

class Follow(models.Model):
    follower = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')  # Prevent duplicate follows

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"

class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')  # Prevent duplicate likes

    def __str__(self):
        return f"Like by {self.user.username} on {self.post.id}"