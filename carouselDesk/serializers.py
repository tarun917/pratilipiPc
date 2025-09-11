from rest_framework import serializers
from .models import CarouselItemModel
import uuid


class CarouselItemSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    target_id = serializers.SerializerMethodField()

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

    def get_target_id(self, obj: CarouselItemModel):
        """
        Ensure digital target_id is always hyphenated UUID in the response.
        Motion remains as-is (string that represents int).
        """
        if not obj.target_id:
            return None
        if obj.type != 'digital':
            return obj.target_id
        try:
            return str(uuid.UUID(str(obj.target_id)))
        except Exception:
            # If somehow invalid, return as-is to avoid breaking
            return obj.target_id