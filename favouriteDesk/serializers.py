from rest_framework import serializers
from .models import FavouriteModel
from digitalcomicDesk.models import ComicModel as DigitalComicModel
from motioncomicDesk.models import ComicModel as MotionComicModel


def canonical_type(t: str | None) -> str | None:
    if not t:
        return None
    t = t.lower()
    if t in ("digital", "digitalcomic"):
        return "digital"
    if t in ("motion", "motioncomic"):
        return "motion"
    return None


class FavouriteSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()

    class Meta:
        model = FavouriteModel
        fields = ["id", "comic_type", "comic_id", "cover_image", "title", "created_at"]

    def _get_comic(self, obj):
        t = canonical_type(obj.comic_type)
        # IMPORTANT: comic_id may be UUID or string; let ORM coerce
        if t == "digital":
            return DigitalComicModel.objects.only("id", "title", "cover_image").filter(id=obj.comic_id).first()
        elif t == "motion":
            return MotionComicModel.objects.only("id", "title", "cover_image").filter(id=obj.comic_id).first()
        return None

    def get_cover_image(self, obj):
        comic = self._get_comic(obj)
        if not comic:
            return None
        img = getattr(comic, "cover_image", None)
        try:
            return img.url if img else None
        except Exception:
            return None

    def get_title(self, obj):
        comic = self._get_comic(obj)
        return getattr(comic, "title", None) or "Unknown"


class FavouriteStatusSerializer(serializers.Serializer):
    is_favourite = serializers.BooleanField()