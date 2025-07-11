from rest_framework import serializers
from .models import NotificationModel

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationModel
        fields = ['id', 'user', 'message', 'timestamp', 'related_tab']