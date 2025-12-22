from rest_framework import serializers
from .models import NotificationModel, DeviceToken


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.SerializerMethodField()

    class Meta:
        model = NotificationModel
        fields = [
            "id",
            "notification_type",
            "related_tab",
            "comic_type",
            "title",
            "message",
            "image_url",
            "deeplink",
            "comic_id",
            "episode_id",
            "is_read",
            "created_at",
            "read_at",
            "ttl",
            "collapse_key",
            "meta",
        ]
        read_only_fields = ["id", "created_at", "read_at", "is_read", "meta"]

    def get_is_read(self, obj: NotificationModel) -> bool:
        return obj.is_read


class DeviceTokenSerializer(serializers.ModelSerializer):
    token = serializers.CharField(max_length=255)
    platform = serializers.ChoiceField(choices=DeviceToken.Platform.choices)

    class Meta:
        model = DeviceToken
        fields = ["token", "platform", "app_version", "locale"]