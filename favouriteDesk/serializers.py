from rest_framework import serializers
from .models import FavouriteModel
from digitalcomicDesk.models import ComicModel as DigitalComicModel
from motioncomicDesk.models import ComicModel as MotionComicModel

class FavouriteSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = FavouriteModel
        fields = ['id', 'comic_type', 'comic_id', 'cover_image', 'title', 'created_at']

    def get_cover_image(self, obj):
        if obj.comic_type == 'digital':
            comic = DigitalComicModel.objects.filter(id=obj.comic_id).first()
        else:  # motion
            comic = MotionComicModel.objects.filter(id=obj.comic_id).first()
        return comic.cover_image.url if comic and comic.cover_image else None

    def get_title(self, obj):
        if obj.comic_type == 'digital':
            comic = DigitalComicModel.objects.filter(id=obj.comic_id).first()
        else:  # motion
            comic = MotionComicModel.objects.filter(id=obj.comic_id).first()
        return comic.title if comic else "Unknown"

class FavouriteStatusSerializer(serializers.Serializer):
    is_favourite = serializers.BooleanField()