from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone

from .models import FavouriteModel
from .serializers import FavouriteSerializer, FavouriteStatusSerializer
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


class FavouriteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    # GET /api/favourite/favourites/?type=digital|motion
    def list(self, request):
        user = request.user
        t = canonical_type(request.query_params.get("type"))
        qs = FavouriteModel.objects.filter(user=user)
        if t:
            qs = qs.filter(comic_type=t)
        serializer = FavouriteSerializer(qs, many=True)
        return Response(serializer.data)

    # POST /api/favourite/favourites/
    # Body: { "comic_type": "digital"|"motion", "comic_id": "<id or uuid>" }
    def create(self, request):
        user = request.user
        t = canonical_type(request.data.get("comic_type"))
        comic_id = request.data.get("comic_id")
        if t not in ("digital", "motion"):
            return Response({"error": "comic_type must be 'digital' or 'motion'"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not comic_id:
            return Response({"error": "comic_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        favourite, created = FavouriteModel.objects.update_or_create(
            user=user,
            comic_type=t,
            comic_id=str(comic_id),
            defaults={"created_at": timezone.now()},
        )
        return Response(
            {"message": "Added to favourites" if created else "Already in favourites"},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    # DELETE /api/favourite/favourites/{comic_type}/{comic_id}/
    # Allow UUID or any string id in the path
    @action(detail=False, methods=['delete'], url_path=r'(?P<comic_type>[^/]+)/(?P<comic_id>[^/]+)')
    def remove(self, request, comic_type=None, comic_id=None):
        user = request.user
        t = canonical_type(comic_type)
        if not t or not comic_id:
            return Response({"error": "comic_type and comic_id required"},
                            status=status.HTTP_400_BAD_REQUEST)
        fav = get_object_or_404(FavouriteModel, user=user, comic_type=t, comic_id=str(comic_id))
        fav.delete()
        return Response({"message": "Removed from favourites"}, status=status.HTTP_200_OK)

    # GET /api/favourite/favourites/status/{comic_type}/{comic_id}/
    @action(detail=False, methods=['get'], url_path=r'status/(?P<comic_type>[^/]+)/(?P<comic_id>[^/]+)')
    def status(self, request, comic_type=None, comic_id=None):
        user = request.user
        t = canonical_type(comic_type)
        if not t or not comic_id:
            return Response({"error": "comic_type and comic_id required"},
                            status=status.HTTP_400_BAD_REQUEST)
        is_favourite = FavouriteModel.objects.filter(
            user=user, comic_type=t, comic_id=str(comic_id)
        ).exists()
        serializer = FavouriteStatusSerializer({"is_favourite": is_favourite})
        return Response(serializer.data)

    # GET /api/favourite/favourites/search/?q=...&type=...
    def _ids_for_query(self, query: str):
        # Helper to get IDs by title query from both models
        digital_ids = DigitalComicModel.objects.filter(title__icontains=query).values_list('id', flat=True)
        motion_ids = MotionComicModel.objects.filter(title__icontains=query).values_list('id', flat=True)
        # Cast to str for consistent comparison with FavouriteModel.comic_id
        return set(map(str, digital_ids)) | set(map(str, motion_ids))

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        user = request.user
        query = (request.query_params.get('q') or '').strip()
        t = canonical_type(request.query_params.get("type"))
        qs = FavouriteModel.objects.filter(user=user)
        if t:
            qs = qs.filter(comic_type=t)
        if query:
            valid_ids = self._ids_for_query(query)
            qs = qs.filter(comic_id__in=valid_ids)
        serializer = FavouriteSerializer(qs, many=True)
        return Response(serializer.data)