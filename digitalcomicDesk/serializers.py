from rest_framework import serializers
from .models import (
    ComicModel,
    EpisodeModel,
    CommentModel,
    SliceModel,
    EpisodeAccess,
)


class ComicSerializer(serializers.ModelSerializer):
    # Keep decimal numeric in JSON
    rating = serializers.DecimalField(max_digits=3, decimal_places=1, coerce_to_string=False)

    class Meta:
        model = ComicModel
        fields = [
            'id',
            'title',
            'genre',
            'cover_image',
            'description',
            'rating',
            'view_count',
            'favourite_count',
            # rating_count intentionally not exposed (unchanged from previous API)
        ]


class SliceSerializer(serializers.ModelSerializer):
    # Expose resolved URL (supports S3 or local storage)
    url = serializers.SerializerMethodField()

    class Meta:
        model = SliceModel
        fields = ['order', 'url', 'width', 'height']

    def get_url(self, obj):
        try:
            return obj.file.url if obj.file else None
        except Exception:
            return None


class EpisodeSerializer(serializers.ModelSerializer):
    # Engagement counters (read-only)
    likes_count = serializers.IntegerField(read_only=True)
    shares_count = serializers.IntegerField(read_only=True)
    comments_count = serializers.IntegerField(read_only=True)
    # Helpful for chaining in UI
    next_episode_id = serializers.SerializerMethodField()

    class Meta:
        model = EpisodeModel
        fields = [
            'id',
            'comic',
            'episode_number',
            'thumbnail',
            'content_url',
            'content_file',
            'is_free',
            'coin_cost',
            'is_locked',
            'likes_count',
            'shares_count',
            'comments_count',
            'next_episode_id',
        ]

    def get_next_episode_id(self, obj):
        nxt = obj.get_next_episode()
        return str(nxt.id) if nxt else None


class CommentChildSerializer(serializers.ModelSerializer):
    """
    Serializer for a reply (child comment).
    """
    class Meta:
        model = CommentModel
        fields = [
            'id',
            'user',
            'parent',
            'comment_text',
            'likes_count',
            'timestamp',
        ]


class CommentSerializer(serializers.ModelSerializer):
    """
    Top-level comment with immediate replies (threaded, shallow).
    """
    replies = serializers.SerializerMethodField()

    class Meta:
        model = CommentModel
        fields = [
            'id',
            'episode',
            'user',
            'parent',
            'comment_text',
            'likes_count',
            'timestamp',
            'replies',
        ]

    def get_replies(self, obj):
        # Only direct replies to avoid deep recursion
        qs = obj.replies.all().order_by('timestamp')
        return CommentChildSerializer(qs, many=True).data


class EpisodeSlicesResponseSerializer(serializers.Serializer):
    """
    Response shape for: GET /episode/<id>/slices
    {
      "episode_id": "<uuid>",
      "next_episode_id": "<uuid>|null",
      "locked": true|false,
      "slices": [{ order, url, width, height }]
    }
    """
    episode_id = serializers.CharField()
    next_episode_id = serializers.CharField(allow_null=True)
    locked = serializers.BooleanField()
    comic_id = serializers.CharField()              # add this
    slices = SliceSerializer(many=True)


class EpisodeAccessSerializer(serializers.ModelSerializer):
    """
    For debugging/admin APIs if needed. Not required for reader flow.
    """
    class Meta:
        model = EpisodeAccess
        fields = ['id', 'user', 'episode', 'source', 'unlocked_at']
        read_only_fields = ['id', 'unlocked_at']