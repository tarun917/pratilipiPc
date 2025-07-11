from rest_framework import serializers
from .models import CoinModel

class CoinSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinModel
        fields = ['id', 'user', 'balance', 'updated_at']
        extra_kwargs = {
            'user': {'required': False},  # Make user optional
        }