# digitalcomicDesk/views.py

from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from .models import (
    ComicModel,
    EpisodeModel,
    CommentModel,
    SliceModel,
    EpisodeAccess,
)
from .serializers import (
    ComicSerializer,
    EpisodeSerializer,
    CommentSerializer,
    SliceSerializer,
)
from .integrations import is_user_premium, debit_coins


class DigitalComicViewSet(viewsets.ModelViewSet):
    """
    Base path:
      /api/digitalcomic/digitalcomic/

    Extra routes:
    - GET    /api/digitalcomic/digitalcomic/<comic_id>/details/
    - POST   /api/digitalcomic/digitalcomic/<comic_id>/unlock/
    - POST   /api/digitalcomic/digitalcomic/<comic_id>/rate/
    - POST   /api/digitalcomic/digitalcomic/<comic_id>/view/
    - POST   /api/digitalcomic/digitalcomic/<comic_id>/favourite/
    - POST   /api/digitalcomic/digitalcomic/<comic_id>/comment/
    - POST   /api/digitalcomic/digitalcomic/<comic_id>/commentlike/
    - POST   /api/digitalcomic/digitalcomic/<comic_id>/episode_like/
    - POST   /api/digitalcomic/digitalcomic/<comic_id>/episode_share/
    - POST   /api/digitalcomic/digitalcomic/<comic_id>/episodes/
    - GET    /api/digitalcomic/digitalcomic/episode/<episode_id>/slices/
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
        episodes = EpisodeModel.objects.filter(comic=comic).order_by('episode_number')
        return Response({
            'comic': self.get_serializer(comic).data,
            'episodes': EpisodeSerializer(episodes, many=True).data
        })

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        """
        Contract:
        - Body: { "episode_id": "<uuid>" }
        - 200: { "unlocked": true, "source": "ALREADY" | "PREMIUM" }
        - 201: { "unlocked": true, "source": "COINS", "balance": <int> }
        - 400: { "error": "<msg>", "code": "bad_request|invalid_episode|insufficient_balance" }
        """
        comic = self.get_object()
        user = request.user
        episode_id = request.data.get('episode_id')

        if not episode_id:
            return Response(
                {"error": "episode_id is required", "code": "bad_request"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        episode = get_object_or_404(EpisodeModel, id=episode_id, comic=comic)

        # Already unlocked?
        if EpisodeAccess.objects.filter(user=user, episode=episode).exists():
            return Response({"unlocked": True, "source": "ALREADY"}, status=status.HTTP_200_OK)

        # Free episode short-circuit (treat as entitlement-like)
        if episode.is_free:
            EpisodeAccess.objects.get_or_create(
                user=user, episode=episode, defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
            )
            return Response({"unlocked": True, "source": "PREMIUM"}, status=status.HTTP_200_OK)

        # Premium entitlement via integration
        if is_user_premium(user):
            EpisodeAccess.objects.get_or_create(
                user=user, episode=episode, defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
            )
            return Response({"unlocked": True, "source": "PREMIUM"}, status=status.HTTP_200_OK)
        
        if not episode.is_locked:
            EpisodeAccess.objects.get_or_create(
                user=user,
                episode=episode,
                defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
            )
            return Response({"unlocked": True, "source": "ALREADY"}, status=status.HTTP_200_OK)

        # Coins path via integration
        coin_cost = episode.coin_cost or 50
        idem_key = f"unlock:user:{user.id}:episode:{episode.id}"
        debit = debit_coins(user=user, amount=coin_cost, idempotency_key=idem_key)
        if not debit.success:
            return Response(
                {"error": debit.error_message or "Insufficient balance", "code": debit.error_code or "insufficient_balance"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        EpisodeAccess.objects.get_or_create(
            user=user, episode=episode, defaults={'source': EpisodeAccess.SOURCE_COINS}
        )
        return Response(
            {"unlocked": True, "source": "COINS", "balance": debit.new_balance},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        comic = self.get_object()
        try:
            rating = float(request.data.get('rating', 0))
        except (TypeError, ValueError):
            return Response({"error": "Invalid rating"}, status=status.HTTP_400_BAD_REQUEST)

        if 1.0 <= rating <= 5.0:
            new_total = (float(comic.rating) * comic.rating_count) + rating
            comic.rating_count += 1
            comic.rating = round(new_total / comic.rating_count, 1)
            comic.save(update_fields=['rating', 'rating_count'])
            return Response({"rating": comic.rating}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid rating"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        comic = self.get_object()
        comic.view_count += 1
        comic.save(update_fields=['view_count'])
        return Response({"view_count": comic.view_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def favourite(self, request, pk=None):
        comic = self.get_object()
        comic.favourite_count += 1
        comic.save(update_fields=['favourite_count'])
        return Response({"favourite_count": comic.favourite_count}, status=status.HTTP_200_OK)

    @transaction.atomic
    @action(detail=True, methods=['post'])
    def comment(self, request, pk=None):
        comic = self.get_object()
        episode_id = request.data.get('episode_id')
        comment_text = request.data.get('comment_text', '').strip()
        parent_id = request.data.get('parent_id')

        if not episode_id or not comment_text:
            return Response({"error": "episode_id and comment_text are required"}, status=status.HTTP_400_BAD_REQUEST)

        episode = get_object_or_404(EpisodeModel, id=episode_id, comic=comic)

        parent = None
        if parent_id:
            parent = get_object_or_404(CommentModel, id=parent_id, episode=episode)

        comment = CommentModel.objects.create(
            episode=episode,
            user=request.user,
            parent=parent,
            comment_text=comment_text
        )

        # Denormalized counter for top-level only
        if parent is None:
            episode.comments_count = (episode.comments_count or 0) + 1
            episode.save(update_fields=['comments_count'])

        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def commentlike(self, request, pk=None):
        comic = self.get_object()
        comment_id = request.data.get('comment_id')
        if not comment_id:
            return Response({"error": "comment_id required"}, status=status.HTTP_400_BAD_REQUEST)

        comment = get_object_or_404(CommentModel, id=comment_id, episode__comic=comic)
        comment.likes_count += 1
        comment.save(update_fields=['likes_count'])
        return Response({"likes_count": comment.likes_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def episode_like(self, request, pk=None):
        comic = self.get_object()
        episode_id = request.data.get('episode_id')
        if not episode_id:
            return Response({"error": "episode_id required"}, status=status.HTTP_400_BAD_REQUEST)
        episode = get_object_or_404(EpisodeModel, id=episode_id, comic=comic)
        episode.likes_count = (episode.likes_count or 0) + 1
        episode.save(update_fields=['likes_count'])
        return Response({"likes_count": episode.likes_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def episode_share(self, request, pk=None):
        comic = self.get_object()
        episode_id = request.data.get('episode_id')
        if not episode_id:
            return Response({"error": "episode_id required"}, status=status.HTTP_400_BAD_REQUEST)
        episode = get_object_or_404(EpisodeModel, id=episode_id, comic=comic)
        episode.shares_count = (episode.shares_count or 0) + 1
        episode.save(update_fields=['shares_count'])
        return Response({"shares_count": episode.shares_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='episodes')
    def create_episode(self, request, pk=None):
        comic = self.get_object()
        serializer = EpisodeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(comic=comic)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Collection-level action for the reader slices endpoint
    @action(detail=False, methods=['get'], url_path=r'episode/(?P<episode_id>[^/.]+)/slices')
    def episode_slices(self, request, episode_id=None):
        """
        Response:
        {
          "episode_id": "<uuid>",
          "next_episode_id": "<uuid>|null",
          "locked": true|false,
          "comic_id": "<uuid>",
          "slices": [{ order, url, width, height }]
        }
        """
        user = request.user
        episode = get_object_or_404(EpisodeModel, id=episode_id)

        is_premium_user = is_user_premium(user)
        has_access = EpisodeAccess.objects.filter(user=user, episode=episode).exists()

        locked = False
        if episode.is_locked and not episode.is_free and not is_premium_user and not has_access:
            locked = True

        slices_qs = SliceModel.objects.filter(episode=episode).order_by('order') if not locked else SliceModel.objects.none()
        slices_data = SliceSerializer(slices_qs, many=True, context={'request': request}).data

        next_ep = episode.get_next_episode()
        payload = {
            "episode_id": str(episode.id),
            "next_episode_id": str(next_ep.id) if next_ep else None,
            "locked": locked,
            "comic_id": str(episode.comic.id),
            "slices": slices_data,
        }
        return Response(payload, status=status.HTTP_200_OK)