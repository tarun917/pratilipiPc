import re
from django.core.exceptions import ValidationError
from rest_framework import serializers
from django.apps import apps  # Added for engagement stats fallback

from profileDesk.models import CustomUser
from profileDesk.serializers import ShortUserSerializer
from .models import Post, Comment, Poll, Vote, Follow, Like
from communityDesk.utils.badges import build_badges_for_user


def _get_or_create_engagement(user):
    """
    Safe getter for communityDesk.UserEngagementStats (used for streak fallback).
    """
    try:
        StatsModel = apps.get_model('communityDesk', 'UserEngagementStats')
    except LookupError:
        return None
    try:
        obj, _ = StatsModel.objects.get_or_create(user=user)
        return obj
    except Exception:
        return None


class CommunityUserSerializer(serializers.ModelSerializer):
    """
    Community-focused user DTO that includes:
     - my_follow_id (relative to request.user)
     - badges (server-computed via shared utility + safe streak fallback)
    """
    my_follow_id = serializers.SerializerMethodField()
    badges = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "full_name",
            "profile_image",
            "badge",          # legacy string (kept for compatibility)
            "my_follow_id",
            "badges",         # server-computed badges
        ]

    def get_my_follow_id(self, obj):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not getattr(user, "is_authenticated", False):
            return None
        rel = Follow.objects.filter(follower=user, following=obj).values("id").first()
        return rel["id"] if rel else None

    def get_badges(self, obj):
        # Primary path: shared utility
        try:
            badges = build_badges_for_user(obj)
        except Exception:
            # Be defensive: never break feed due to badges logic
            badges = []

        # Fallback: ensure streak badge if streak_days > 0 (aligns with Profile view behavior)
        es = _get_or_create_engagement(obj)
        try:
            streak_days = (getattr(es, "streak_days", 0) or 0) if es else 0
            if streak_days > 0:
                has_streak = any(
                    isinstance(b, dict) and b.get("type", "").lower() == "streak"
                    for b in badges
                )
                if not has_streak:
                    badges.append({
                        "type": "streak",
                        "label": f"{streak_days}-day streak",
                        "days": streak_days,
                    })
        except Exception:
            # Ignore fallback failure silently; badges remain as-is
            pass

        return badges


class PostSerializer(serializers.ModelSerializer):
    # Use community-aware user serializer so UI gets 'my_follow_id' and 'badges' on authors
    user = CommunityUserSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    poll = serializers.SerializerMethodField()  # Show only first poll, if exists

    class Meta:
        model = Post
        fields = [
            "id",
            "user",
            "text",
            "image_url",
            "hashtags",
            "commenting_enabled",
            "like_count",
            "comment_count",
            "is_liked",
            "share_count",
            "poll",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "image_url": {"required": False},
            "hashtags": {"required": False},
        }

    def validate_hashtags(self, value):
        # Accept hashtags as a space-separated string, e.g., '#tarun #bhawin'
        if not value:
            return []
        if isinstance(value, str):
            hashtags = [tag for tag in value.strip().split() if tag]
        else:
            hashtags = value
        if not all(isinstance(tag, str) and re.match(r"^\#\w+$", tag) for tag in hashtags):
            raise ValidationError(
                "Hashtags must start with # and contain only letters, numbers, or underscores."
            )
        return hashtags

    def get_like_count(self, obj):
        return Like.objects.filter(post=obj).count()

    def get_comment_count(self, obj):
        return Comment.objects.filter(post=obj).count()

    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and hasattr(request, "user") and request.user.is_authenticated:
            return Like.objects.filter(post=obj, user=request.user).exists()
        return False

    def get_poll(self, obj):
        poll = Poll.objects.filter(post=obj).first()
        if poll:
            # Show my_vote also if user is authenticated
            poll_data = PollSerializer(poll).data
            request = self.context.get("request")
            if request and hasattr(request, "user") and request.user.is_authenticated:
                vote = Vote.objects.filter(poll=poll, user=request.user).first()
                poll_data["my_vote"] = vote.option_id if vote else None
            else:
                poll_data["my_vote"] = None
            return poll_data
        return None

    def validate_text(self, value):
        if not value.strip():
            raise ValidationError("Text cannot be empty.")
        if len(value) > 512:
            raise ValidationError("Text must not exceed 512 characters.")
        if not any(c.isalnum() for c in value):
            raise ValidationError("Text must contain at least one alphanumeric character.")
        return value


class CommentSerializer(serializers.ModelSerializer):
    # Allow user/post to be set automatically via view; present nested user details as ShortUserSerializer
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), required=False)
    user = ShortUserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ["id", "post", "user", "text", "created_at"]

    def validate_text(self, value):
        if not value.strip():
            raise ValidationError("Text cannot be empty.")
        if len(value) > 256:
            raise ValidationError("Text must not exceed 256 characters.")
        return value


class PollSerializer(serializers.ModelSerializer):
    # Allow post to be set automatically
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), required=False)

    class Meta:
        model = Poll
        fields = ["id", "post", "question", "options", "votes", "created_at"]

    def validate_options(self, value):
        if not isinstance(value, dict) or len(value) < 2 or len(value) > 6:
            raise ValidationError("Options must be a dictionary with 2 to 6 entries.")
        return value

    def validate(self, data):
        if "options" in data and "votes" in data and set(data["votes"].keys()) != set(data["options"].keys()):
            raise ValidationError("Votes keys must match options keys.")
        return data


class VoteSerializer(serializers.ModelSerializer):
    # Allow poll/user to be set automatically
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    poll = serializers.PrimaryKeyRelatedField(queryset=Poll.objects.all(), required=False)

    class Meta:
        model = Vote
        fields = ["id", "poll", "user", "option_id", "created_at"]
        extra_kwargs = {
            "option_id": {"required": True},
        }

    def validate_option_id(self, value):
        poll = self.context["request"].data.get("poll")
        if poll:
            poll_obj = Poll.objects.get(id=poll.id)
            if value not in poll_obj.options.keys():
                raise ValidationError("Invalid option ID.")
        return value

    def validate(self, data):
        if Vote.objects.filter(poll=data["poll"], user=data["user"]).exists():
            raise ValidationError("You have already voted in this poll.")
        return data


class FollowSerializer(serializers.ModelSerializer):
    follower = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    following = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = Follow
        fields = ["id", "follower", "following", "created_at"]

    def validate(self, data):
        if data["follower"] == data["following"]:
            raise ValidationError("You cannot follow yourself.")
        if Follow.objects.filter(follower=data["follower"], following=data["following"]).exists():
            raise ValidationError("You are already following this user.")
        return data


class LikeSerializer(serializers.ModelSerializer):
    # Allow post/user to be set automatically
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), required=False)

    class Meta:
        model = Like
        fields = ["id", "post", "user", "created_at"]

    def validate(self, data):
        if Like.objects.filter(post=data["post"], user=data["user"]).exists():
            raise ValidationError("You have already liked this post.")
        return data