from rest_framework import serializers
from .models import CarouselItemModel


class CarouselItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = CarouselItemModel
        fields = ['id', 'image_url', 'type', 'order', 'target_id']

    def get_image_url(self, obj: CarouselItemModel):
        # Return absolute URL if possible
        if not obj.image_url:
            return None
        request = self.context.get('request')
        url = obj.image_url.url
        return request.build_absolute_uri(url) if request else url
