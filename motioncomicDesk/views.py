from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ComicModel, EpisodeModel, CommentModel, EpisodeAccess
from .serializers import ComicSerializer, EpisodeSerializer, CommentSerializer


class MotionComicViewSet(viewsets.ModelViewSet):
    """
    Routes:
    - GET /api/motioncomic/motioncomic/?genre=
    - GET /api/motioncomic/motioncomic/{comic_id}/details/
    - POST /api/motioncomic/motioncomic/{comic_id}/unlock/   body: { episode_id }
      Response:
        200 -> { unlocked: true, source: "PREMIUM" | "ALREADY", balance? }
        201 -> { unlocked: true, source: "COINS", balance }
        400 -> { error, code?: "insufficient_balance" }
    - Additional actions: rate, view, like, comment, commentlike, share, favourite, create_episode
    """
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

    def _is_user_premium(self, user) -> bool:
        # Replace with premiumDesk integration if available
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        if getattr(user, 'is_premium', False):
            return True
        if hasattr(user, 'subscriptionmodel_set'):
            try:
                return user.subscriptionmodel_set.exists()
            except Exception:
                return False
        return False

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """
        Per-user unlock logic (parity with digital):
        - If EpisodeAccess exists -> ALREADY (no charge)
        - If episode is globally unlocked (admin) -> ALREADY (safety guard; no charge)
        - If user is premium or episode is free -> PREMIUM grant for this episode (no charge)
        - Else coins path: check balance, deduct once, create EpisodeAccess
        """
        comic = self.get_object()
        user = request.user
        episode_id = request.data.get('episode_id')

        # Validate episode
        if episode_id:
            episode = EpisodeModel.objects.filter(id=episode_id, comic=comic).first()
        else:
            episode = None

        if not episode:
            return Response({"error": "Valid episode_id required for this comic"}, status=status.HTTP_400_BAD_REQUEST)

        # Idempotency: already unlocked for this user
        if EpisodeAccess.objects.filter(user=user, episode=episode).exists():
            return Response({"unlocked": True, "source": "ALREADY", "episode_id": episode.id}, status=status.HTTP_200_OK)

        # Safety guard: admin globally unlocked -> do not charge, mark as ALREADY
        if not episode.is_locked:
            EpisodeAccess.objects.get_or_create(user=user, episode=episode, defaults={'source': EpisodeAccess.SOURCE_PREMIUM})
            return Response({"unlocked": True, "source": "ALREADY", "episode_id": episode.id}, status=status.HTTP_200_OK)

        # Premium or Free episode -> grant without coins
        if episode.is_free or self._is_user_premium(user):
            EpisodeAccess.objects.get_or_create(
                user=user, episode=episode,
                defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
            )
            return Response({"unlocked": True, "source": "PREMIUM", "episode_id": episode.id}, status=status.HTTP_200_OK)

        # Coins path
        cost = episode.coin_cost or 50
        balance = getattr(user, 'coin_count', 0)
        if balance < cost:
            return Response(
                {"error": "Insufficient coins", "code": "insufficient_balance", "required": cost, "balance": balance},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Deduct and grant atomically
        with transaction.atomic():
            # Re-check idempotency inside tx
            if EpisodeAccess.objects.select_for_update().filter(user=user, episode=episode).exists():
                return Response({"unlocked": True, "source": "ALREADY", "episode_id": episode.id}, status=status.HTTP_200_OK)

            # Deduct simple balance (replace with WalletLedger when available)
            user.coin_count = balance - cost
            user.save(update_fields=['coin_count'])

            EpisodeAccess.objects.create(user=user, episode=episode, source=EpisodeAccess.SOURCE_COINS)

        return Response(
            {"unlocked": True, "source": "COINS", "episode_id": episode.id, "balance": user.coin_count},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        comic = self.get_object()
        rating = request.data.get('rating', 0)
        try:
            rating = float(rating)
        except (TypeError, ValueError):
            return Response({"error": "Invalid rating"}, status=status.HTTP_400_BAD_REQUEST)
        if 1 <= rating <= 5:
            # Weighted average
            comic.rating = ((comic.rating * comic.rating_count) + rating) / (comic.rating_count + 1)
            comic.rating_count += 1
            comic.save(update_fields=['rating', 'rating_count'])
            return Response({"rating": float(comic.rating)}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid rating"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        comic = self.get_object()
        comic.view_count += 1
        comic.save(update_fields=['view_count'])
        return Response({"view_count": comic.view_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        comic = self.get_object()
        comic.favourite_count += 1
        comic.save(update_fields=['favourite_count'])
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
            comment.save(update_fields=['likes_count'])
            return Response({"likes_count": comment.likes_count}, status=status.HTTP_200_OK)
        return Response({"error": "Comment ID required"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        comic = self.get_object()
        comic.favourite_count += 1  # simple placeholder metric
        comic.save(update_fields=['favourite_count'])
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
    GET /api/motioncomic/motioncomic/episode/{id}/
    Returns single episode with per-user lock, prev/next, playback_url.
    """
    queryset = EpisodeModel.objects.all()
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, context={'request': request})
        return Response(serializer.data)