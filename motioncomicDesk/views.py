from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ComicModel, EpisodeModel, CommentModel, UserEpisodeUnlock
from .serializers import ComicSerializer, EpisodeSerializer, CommentSerializer


class MotionComicViewSet(viewsets.ModelViewSet):
    queryset = ComicModel.objects.all()
    serializer_class = ComicSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        genre = request.query_params.get('genre', '')
        queryset = self.queryset
        if genre:
            queryset = queryset.filter(genre=genre)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        comic = self.get_object()
        # Return episodes sorted by episode_number
        episodes = EpisodeModel.objects.filter(comic=comic).order_by('episode_number')
        return Response({
            'comic': self.get_serializer(comic).data,
            'episodes': EpisodeSerializer(episodes, many=True, context={'request': request}).data
        })

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """
        Per-user unlock logic:
        - If user is premium -> create unlock records for all episodes (for this user only)
        - Else:
          - Deduct coins (episode.coin_cost, default 50)
          - Create a UserEpisodeUnlock for the requested episode
        """
        comic = self.get_object()
        user = request.user
        episode_id = request.data.get('episode_id')

        # Premium: unlock all episodes for this user
        if hasattr(user, 'subscriptionmodel_set') and user.subscriptionmodel_set.exists():
            episodes = EpisodeModel.objects.filter(comic=comic)
            created_count = 0
            for ep in episodes:
                _, created = UserEpisodeUnlock.objects.get_or_create(user=user, episode=ep)
                if created:
                    created_count += 1
            return Response({"message": "All episodes unlocked (premium)", "created": created_count}, status=status.HTTP_200_OK)

        # Non-premium path: need episode
        if episode_id:
            episode = EpisodeModel.objects.filter(id=episode_id, comic=comic).first()
        else:
            episode = EpisodeModel.objects.filter(comic=comic).order_by('episode_number').first()

        if not episode:
            return Response({"error": "No episodes found for this comic"}, status=status.HTTP_400_BAD_REQUEST)

        # Already unlocked?
        if UserEpisodeUnlock.objects.filter(user=user, episode=episode).exists():
            return Response({"message": "Already unlocked", "episode_id": episode.id}, status=status.HTTP_200_OK)

        # Check coin balance
        cost = episode.coin_cost or 50
        if getattr(user, 'coin_count', 0) < cost:
            return Response({"error": "Insufficient coins", "required": cost, "balance": getattr(user, 'coin_count', 0)}, status=status.HTTP_400_BAD_REQUEST)

        # Deduct and unlock
        user.coin_count -= cost
        user.save()
        UserEpisodeUnlock.objects.create(user=user, episode=episode)

        return Response({"message": "Episode unlocked", "episode_id": episode.id, "coin_balance": user.coin_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        comic = self.get_object()
        rating = request.data.get('rating', 0)
        try:
            rating = float(rating)
        except (TypeError, ValueError):
            return Response({"error": "Invalid rating"}, status=status.HTTP_400_BAD_REQUEST)
        if 1 <= rating <= 5:
            comic.rating = ((comic.rating * comic.rating_count) + rating) / (comic.rating_count + 1)
            comic.rating_count += 1
            comic.save()
            return Response({"rating": comic.rating}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid rating"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        comic = self.get_object()
        comic.view_count += 1
        comic.save()
        return Response({"view_count": comic.view_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        comic = self.get_object()
        comic.favourite_count += 1
        comic.save()
        return Response({"favourite_count": comic.favourite_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def comment(self, request, pk=None):
        comic = self.get_object()
        episode_id = request.data.get('episode_id')
        comment_text = request.data.get('comment_text')
        if episode_id and comment_text:
            episode = get_object_or_404(EpisodeModel, id=episode_id, comic=comic)
            comment = CommentModel.objects.create(episode=episode, user=request.user, comment_text=comment_text)
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        return Response({"error": "Episode ID and comment text required"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def commentlike(self, request, pk=None):
        comic = self.get_object()
        comment_id = request.data.get('comment_id')
        if comment_id:
            comment = get_object_or_404(CommentModel, id=comment_id, episode__comic=comic)
            comment.likes_count += 1
            comment.save()
            return Response({"likes_count": comment.likes_count}, status=status.HTTP_200_OK)
        return Response({"error": "Comment ID required"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        comic = self.get_object()
        comic.favourite_count += 1  # Assuming share increases favourite count
        comic.save()
        return Response({"favourite_count": comic.favourite_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def favourite(self, request, pk=None):
        # Placeholder for wishlist integration
        return Response({"message": "Added to favourites"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='episodes')
    def create_episode(self, request, pk=None):
        comic = self.get_object()
        serializer = EpisodeSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(comic=comic)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EpisodeViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    GET /api/motioncomic/episode/{id}/  -> single episode with per-user lock, prev/next, playback_url
    """
    queryset = EpisodeModel.objects.all()
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return Response(serializer.data)