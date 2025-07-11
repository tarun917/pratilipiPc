from rest_framework import serializers
from .models import CarouselItemModel

class CarouselItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CarouselItemModel
        fields = ['id', 'image_url', 'type', 'order']