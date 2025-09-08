from rest_framework import serializers
from .models import ComicModel, EpisodeModel, CommentModel, EpisodeAccess


class ComicSerializer(serializers.ModelSerializer):
    # Keep coerce_to_string=False to return Decimal as number
    rating = serializers.DecimalField(max_digits=3, decimal_places=1, coerce_to_string=False)

    class Meta:
        model = ComicModel
        fields = ['id', 'title', 'genre', 'cover_image', 'description', 'rating', 'view_count', 'favourite_count']


class EpisodeSerializer(serializers.ModelSerializer):
    # New computed fields
    is_locked_for_user = serializers.SerializerMethodField()
    prev_episode_id = serializers.SerializerMethodField()
    next_episode_id = serializers.SerializerMethodField()
    playback_url = serializers.SerializerMethodField()  # resolves video_url or video_file URL

    class Meta:
        model = EpisodeModel
        fields = [
            'id', 'comic', 'episode_number', 'thumbnail',
            'video_url', 'video_file', 'is_free', 'coin_cost',
            'is_locked',  # admin-level lock (compat); clients should use is_locked_for_user
            'short_description',
            # Computed fields for app
            'is_locked_for_user', 'prev_episode_id', 'next_episode_id', 'playback_url',
        ]

    def _is_user_premium(self, user) -> bool:
        # Fallback heuristic:
        # 1) user.is_premium boolean if present
        # 2) subscriptionmodel_set exists and is non-empty
        # Replace with premiumDesk integration if available.
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'is_premium', False):
            return True
        if hasattr(user, 'subscriptionmodel_set'):
            try:
                return user.subscriptionmodel_set.exists()
            except Exception:
                return False
        return False

    def get_is_locked_for_user(self, obj: EpisodeModel) -> bool:
        request = self.context.get('request', None)
        user = getattr(request, 'user', None)

        # Anonymous or no user context -> treat as locked
        if not user or not getattr(user, 'is_authenticated', False):
            return True

        # If episode marked free -> unlocked
        if obj.is_free:
            return False

        # If admin has globally unlocked -> unlocked
        if not obj.is_locked:
            return False

        # Premium users unlock all
        if self._is_user_premium(user):
            return False

        # Per-user access
        return not EpisodeAccess.objects.filter(user=user, episode=obj).exists()

    def get_prev_episode_id(self, obj: EpisodeModel):
        prev = EpisodeModel.objects.filter(comic=obj.comic, episode_number=obj.episode_number - 1).only('id').first()
        return prev.id if prev else None

    def get_next_episode_id(self, obj: EpisodeModel):
        nxt = EpisodeModel.objects.filter(comic=obj.comic, episode_number=obj.episode_number + 1).only('id').first()
        return nxt.id if nxt else None

    def get_playback_url(self, obj: EpisodeModel):
        # Prefer explicit video_url, else video_file.url if present
        if obj.video_url:
            return obj.video_url
        if obj.video_file:
            try:
                request = self.context.get('request', None)
                url = obj.video_file.url
                return request.build_absolute_uri(url) if request else url
            except Exception:
                return None
        return None


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentModel
        fields = ['id', 'episode', 'user', 'comment_text', 'likes_count', 'timestamp']