from rest_framework import serializers
from .models import ReadingActivity

class InProgressItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingActivity
        fields = [
            "type", "comic_id", "episode_id",
            "comic_title", "episode_label", "cover_url",
            "progress_percent", "position_ms", "last_read_at",
        ]

class FinishedItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingActivity
        fields = [
            "type", "comic_id",
            "comic_title", "cover_url",
            "finished_at",
        ]

class ProgressWriteSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=["digital", "motion"])
    comic_id = serializers.IntegerField()
    episode_id = serializers.IntegerField(required=False, allow_null=True)
    progress_percent = serializers.FloatField(min_value=0, max_value=100)
    position_ms = serializers.IntegerField(required=False, allow_null=True)
    comic_title = serializers.CharField(required=False, allow_blank=True, default="")
    episode_label = serializers.CharField(required=False, allow_blank=True, default="")
    cover_url = serializers.URLField(required=False, allow_blank=True)