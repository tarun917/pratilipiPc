from rest_framework import serializers
from .models import ComicModel, EpisodeModel, CommentModel
from django.db.models import DecimalField

class ComicSerializer(serializers.ModelSerializer):
    rating = serializers.DecimalField(max_digits=3, decimal_places=1, coerce_to_string=False)
    class Meta:
        model = ComicModel
        fields = ['id', 'title', 'genre', 'cover_image', 'description', 'rating', 'view_count', 'favourite_count']
        

class EpisodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = EpisodeModel
        fields = ['id', 'comic', 'episode_number', 'thumbnail', 'video_url', 'is_free', 'coin_cost', 'is_locked', 'short_description']

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommentModel
        fields = ['id', 'episode', 'user', 'comment_text', 'likes_count', 'timestamp']