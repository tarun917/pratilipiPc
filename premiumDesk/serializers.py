from rest_framework import serializers
from .models import SubscriptionModel

class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionModel
        fields = ['id', 'user', 'plan', 'price', 'benefits', 'start_date', 'end_date']
        extra_kwargs = {
            'user': {'required': False},  # Make user optional
        }