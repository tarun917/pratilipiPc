from uuid import UUID

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from django.core.cache import cache
from .models import FavouriteModel
from .serializers import FavouriteSerializer, FavouriteStatusSerializer
from digitalcomicDesk.models import ComicModel as DigitalComicModel
from motioncomicDesk.models import ComicModel as MotionComicModel  # fixed import


def canonical_type(t: str | None) -> str | None:
    if not t:
        return None
    t = t.lower()
    if t in ("digital", "digitalcomic"):
        return "digital"
    if t in ("motion", "motioncomic"):
        return "motion"
    return None


def alias_types(t: str | None) -> list[str]:
    """
    Return a list containing the canonical type and its alias for cleanup/compat checks.
    """
    ct = canonical_type(t)
    if ct == "digital":
        return ["digital", "digitalcomic"]
    if ct == "motion":
        return ["motion", "motioncomic"]
    return []


def _normalize_id(value: str) -> str:
    """
    Normalize IDs so future lookups are consistent.
    - If it parses as a UUID, store lower-case canonical string.
    - Otherwise, return string as-is.
    """
    try:
        return str(UUID(str(value))).lower()
    except Exception:
        return str(value)


class FavouriteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    # GET /api/favourite/favourites/?type=digital|motion
    def list(self, request):
        user = request.user
        t = canonical_type(request.query_params.get("type"))
        qs = FavouriteModel.objects.filter(user=user)
        if t:
            # Only return canonical type to prevent duplicates in clients
            qs = qs.filter(comic_type=t)
        serializer = FavouriteSerializer(qs, many=True)
        return Response(serializer.data)

    # POST /api/favourite/favourites/
    # Body: { "comic_type": "digital"|"motion", "comic_id": "<id or uuid>" }
    def create(self, request):
        user = request.user
        t = canonical_type(request.data.get("comic_type"))
        comic_id_raw = request.data.get("comic_id")
        if t not in ("digital", "motion"):
            return Response(
                {"error": "comic_type must be 'digital' or 'motion'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if not comic_id_raw:
            return Response({"error": "comic_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate target exists (case-insensitive for digital UUIDs)
        if t == "digital":
            exists = DigitalComicModel.objects.filter(id__iexact=comic_id_raw).exists()
        else:  # motion
            exists = MotionComicModel.objects.filter(id=comic_id_raw).exists()
        if not exists:
            return Response(
                {"error": f"{t} comic with id '{comic_id_raw}' not found"},
                status=status.HTTP_400_BAD_REQUEST
            )
        

        key = f"fav:recently_deleted:{user.id}:{t}:{str(comic_id_raw).lower()}"
        if cache.get(key):
    # Ignore accidental auto re-add right after delete
            return Response({"message": "Skipped re-add (just removed)"}, status=status.HTTP_200_OK)

        # Normalize stored id (UUID -> lower-case canonical)
        stored_id = _normalize_id(comic_id_raw)

        # Cleanup any legacy alias rows to avoid duplicates
        # e.g., if an older row exists with comic_type='digitalcomic'
        FavouriteModel.objects.filter(
            user=user,
            comic_type__in=alias_types(t),
            # Case-insensitive match for digital UUIDs
            **(
                {"comic_id__iexact": stored_id}
                if t == "digital" else
                {"comic_id": stored_id}
            )
        ).delete()

        # Create under the canonical type only
        favourite, created = FavouriteModel.objects.update_or_create(
            user=user,
            comic_type=t,
            comic_id=stored_id,
            defaults={"created_at": timezone.now()},
        )
        return Response(
            {"message": "Added to favourites" if created else "Already in favourites"},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    # DELETE /api/favourite/favourites/{comic_type}/{comic_id}/
    @action(detail=False, methods=['delete'], url_path=r'(?P<comic_type>[^/]+)/(?P<comic_id>[^/]+)')
    def remove(self, request, comic_type=None, comic_id=None):
        user = request.user
        t = canonical_type(comic_type)
        if not t or not comic_id:
            return Response(
                {"error": "comic_type and comic_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        key = f"fav:recently_deleted:{user.id}:{t}:{str(comic_id).lower()}"
        cache.set(key, True, timeout=10)  # 10 seconds window

        # Build a queryset that removes both canonical and alias types to prevent reappearance
        type_set = alias_types(t)
        if t == "digital":
            qs = FavouriteModel.objects.filter(
                user=user,
                comic_type__in=type_set,
                comic_id__iexact=str(comic_id)
            )
        else:
            qs = FavouriteModel.objects.filter(
                user=user,
                comic_type__in=type_set,
                comic_id=str(comic_id)
            )

        deleted, _ = qs.delete()
        if deleted == 0:
            # Keep 404 for proper semantics, but we already cover both types and case-insensitive for digital
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)

    # GET /api/favourite/favourites/status/{comic_type}/{comic_id}/
    @action(detail=False, methods=['get'], url_path=r'status/(?P<comic_type>[^/]+)/(?P<comic_id>[^/]+)')
    def status(self, request, comic_type=None, comic_id=None):
        user = request.user
        t = canonical_type(comic_type)
        if not t or not comic_id:
            return Response(
                {"error": "comic_type and comic_id required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Consider both canonical and alias types to report accurate status
        type_set = alias_types(t)
        if t == "digital":
            is_favourite = FavouriteModel.objects.filter(
                user=user,
                comic_type__in=type_set,
                comic_id__iexact=str(comic_id)
            ).exists()
        else:
            is_favourite = FavouriteModel.objects.filter(
                user=user,
                comic_type__in=type_set,
                comic_id=str(comic_id)
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