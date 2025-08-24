from rest_framework import serializers
from .models import ComicModel, EpisodeModel, CommentModel, UserEpisodeUnlock


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
            'is_locked',  # kept for compatibility; clients should use is_locked_for_user
            'short_description',
            # new fields for app
            'is_locked_for_user', 'prev_episode_id', 'next_episode_id', 'playback_url',
        ]

    def get_is_locked_for_user(self, obj: EpisodeModel):
        request = self.context.get('request', None)
        user = getattr(request, 'user', None)
        # Anonymous or no user context -> locked
        if not user or not user.is_authenticated:
            return True
        # Premium: unlock all
        if hasattr(user, 'subscriptionmodel_set') and user.subscriptionmodel_set.exists():
            return False
        # Per-user unlock record
        return not UserEpisodeUnlock.objects.filter(user=user, episode=obj).exists()

    def get_prev_episode_id(self, obj: EpisodeModel):
        prev = EpisodeModel.objects.filter(comic=obj.comic, episode_number=obj.episode_number - 1).first()
        return prev.id if prev else None

    def get_next_episode_id(self, obj: EpisodeModel):
        nxt = EpisodeModel.objects.filter(comic=obj.comic, episode_number=obj.episode_number + 1).first()
        return nxt.id if nxt else None

    def get_playback_url(self, obj: EpisodeModel):
        # Prefer explicit video_url, else video_file.url if present
        if obj.video_url:
            return obj.video_url
        if obj.video_file:
            try:
                request = self.context.get('request', None)
                # Absolute URL if request is available
                url = obj.video_file.url
                return request.build_absolute_uri(url) if request else url
            except Exception:
                return None
        return None


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentModel
        fields = ['id', 'episode', 'user', 'comment_text', 'likes_count', 'timestamp']