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
    # Threaded replies: parent is self-FK
    parent = models.ForeignKey('self', null=True, blank=True, related_name='replies', on_delete=models.CASCADE)
    text = models.TextField(max_length=256)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['post', 'parent', '-created_at']),
            models.Index(fields=['post', '-created_at']),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on {self.post.id}"


class Poll(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    question = models.CharField(max_length=255)
    options = models.JSONField(default=dict)  # e.g., {"1": "Option 1", "2": "Option 2"}
    votes = models.JSONField(default=dict)    # e.g., {"1": 5, "2": 3"}
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
        indexes = [
            models.Index(fields=['follower', 'following']),
            models.Index(fields=['following']),
            models.Index(fields=['follower']),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')  # Prevent duplicate likes
        indexes = [
            models.Index(fields=['post', 'user']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Like by {self.user.username} on {self.post.id}"


# ========= Badge/engagement support =========

class UserEngagementStats(models.Model):
    """
    Aggregate engagement stats per user.
    These counters power Reader/Motion/Streak badges and leaderboard scoring.

    Populate/maintain these from your Digital/Motion/Profile apps:
      - Increment comic_read_count when a chapter/episode is read to completion.
      - Increment motion_watch_count when a motion episode is watched to completion.
      - Maintain streak_days once per day when there is any qualifying activity.
        (or via a daily 'ping' endpoint if you choose to count app opens)
    """
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='engagement_stats')
    comic_read_count = models.PositiveIntegerField(default=0)
    motion_watch_count = models.PositiveIntegerField(default=0)
    streak_days = models.PositiveIntegerField(default=0)
    last_activity_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['streak_days']),
            models.Index(fields=['comic_read_count']),
            models.Index(fields=['motion_watch_count']),
        ]
        verbose_name = "User Engagement Stats"
        verbose_name_plural = "User Engagement Stats"

    def __str__(self):
        return f"Stats<{self.user.username}> R:{self.comic_read_count} M:{self.motion_watch_count} S:{self.streak_days}"