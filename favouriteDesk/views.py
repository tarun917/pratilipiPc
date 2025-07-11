from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import FavouriteModel
from .serializers import FavouriteSerializer, FavouriteStatusSerializer  # To be created in next step
from django.shortcuts import get_object_or_404
from django.utils import timezone  # Replaced django.db.models for better timezone support
from digitalcomicDesk.models import ComicModel as DigitalComicModel
from motioncomicDesk.models import ComicModel as MotionComicModel

class FavouriteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Return all favourites for the authenticated user."""
        user = request.user
        favourites = FavouriteModel.objects.filter(user=user)
        serializer = FavouriteSerializer(favourites, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def add(self, request):
        """Add a new favourite for the authenticated user."""
        user = request.user
        comic_type = request.data.get('comic_type')
        comic_id = request.data.get('comic_id')
        if comic_type not in ['digital', 'motion'] or not comic_id:
            return Response({"error": "Invalid comic type or ID"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            FavouriteModel.objects.update_or_create(
                user=user,
                comic_type=comic_type,
                comic_id=comic_id,
                defaults={'created_at': timezone.now()}  # Using timezone.now() for precision
            )
            return Response({"message": "Added to favourites"}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['delete'], url_path='remove/(?P<comic_id>\d+)')
    def remove(self, request, comic_id=None):
        """Remove a favourite for the authenticated user."""
        user = request.user
        if not comic_id:
            return Response({"error": "Comic ID required"}, status=status.HTTP_400_BAD_REQUEST)
        favourite = get_object_or_404(FavouriteModel, user=user, comic_id=comic_id)
        favourite.delete()
        return Response({"message": "Removed from favourites"}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='status/(?P<comic_id>\d+)')
    def status(self, request, comic_id=None):
        """Check if a comic is favourited by the authenticated user."""
        user = request.user
        if not comic_id:
            return Response({"error": "Comic ID required"}, status=status.HTTP_400_BAD_REQUEST)
        is_favourite = FavouriteModel.objects.filter(user=user, comic_id=comic_id).exists()
        serializer = FavouriteStatusSerializer({"is_favourite": is_favourite})
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='search')
    def search(self, request):
        """Search favourites by title for the authenticated user."""
        user = request.user
        query = request.query_params.get('q', '').lower()
        favourites = FavouriteModel.objects.filter(user=user)
        if query:
            # Optimize by filtering ComicModel once and mapping back
            digital_comics = DigitalComicModel.objects.filter(title__icontains=query)
            motion_comics = MotionComicModel.objects.filter(title__icontains=query)
            valid_comic_ids = set(digital_comics.values_list('id', flat=True)) | set(motion_comics.values_list('id', flat=True))
            filtered_favourites = favourites.filter(comic_id__in=valid_comic_ids)
        else:
            filtered_favourites = favourites
        serializer = FavouriteSerializer(filtered_favourites, many=True)
        return Response(serializer.data)