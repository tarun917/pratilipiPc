from django.shortcuts import get_object_or_404
from django.db import transaction
from django.apps import apps
from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from readingActivityDesk.models import ReadingActivity

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


# -------------------------
# Engagement utilities (safe)
# -------------------------
def _get_or_create_engagement(user):
    """
    Get/create communityDesk.UserEngagementStats for the user (safe even if app missing).
    """
    try:
        StatsModel = apps.get_model('communityDesk', 'UserEngagementStats')
    except LookupError:
        return None

    try:
        obj, _ = StatsModel.objects.get_or_create(user=user)
        return obj
    except Exception:
        return None


def _bump_streak(es):
    """
    Maintain streak_days and last_activity_date.
    Rules:
    - First activity or last activity is before yesterday -> set streak_days = 1
    - Last activity is yesterday -> streak_days += 1
    - Last activity is today -> no change
    """
    if es is None:
        return

    try:
        today = timezone.localdate()
        last = es.last_activity_date
        if last == today:
            # Already counted for today
            return
        if last is None:
            es.streak_days = max(1, es.streak_days or 0)
        else:
            delta = (今天 - last).days if False else (today - last).days  # defensive: keep original behavior
            if delta == 1:
                es.streak_days = (es.streak_days or 0) + 1
            else:
                # Gap >=2 days resets streak to 1 for today
                es.streak_days = 1
        es.last_activity_date = today
    except Exception:
        # Never block main flow
        pass


def _bump_reader_on_new_access(user, new_access_created: bool):
    """
    If we actually created a NEW EpisodeAccess just now, increment comic_read_count
    and update streak safely.
    """
    if not new_access_created:
        # Nothing to bump if user already had access
        return
    es = _get_or_create_engagement(user)
    if es is None:
        return
    try:
        es.comic_read_count = (es.comic_read_count or 0) + 1
        _bump_streak(es)
        es.save(update_fields=['comic_read_count', 'streak_days', 'last_activity_date', 'updated_at'])
    except Exception:
        pass


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
    - NEW:
      - POST  /api/digitalcomic/digitalcomic/<comic_id>/progress/
      - POST  /api/digitalcomic/digitalcomic/<comic_id>/mark-finished/
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
            _, created = EpisodeAccess.objects.get_or_create(
                user=user, episode=episode, defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
            )
            _bump_reader_on_new_access(user, created)
            return Response({"unlocked": True, "source": "PREMIUM"}, status=status.HTTP_200_OK)

        # Premium entitlement via integration
        if is_user_premium(user):
            _, created = EpisodeAccess.objects.get_or_create(
                user=user, episode=episode, defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
            )
            _bump_reader_on_new_access(user, created)
            return Response({"unlocked": True, "source": "PREMIUM"}, status=status.HTTP_200_OK)

        # Globally unlocked episode (admin)
        if not episode.is_locked:
            _, created = EpisodeAccess.objects.get_or_create(
                user=user,
                episode=episode,
                defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
            )
            _bump_reader_on_new_access(user, created)
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

        _, created = EpisodeAccess.objects.get_or_create(
            user=user, episode=episode, defaults={'source': EpisodeAccess.SOURCE_COINS}
        )
        _bump_reader_on_new_access(user, created)
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

    # --- Reading Activity: progress upsert (Digital) ---
    @action(detail=True, methods=['post'], url_path='progress')
    def progress(self, request, pk=None):
        """
        Upsert reading progress for this comic.
        Body:
          {
            "episode_id": "<uuid>",
            "progress_percent": 0..100,
            "comic_title": "...",        (optional)
            "episode_label": "...",      (optional)
            "cover_url": "https://..."   (optional)
          }
        """
        comic = self.get_object()
        user = request.user
        episode_id = request.data.get('episode_id')
        progress_percent = request.data.get('progress_percent')

        if episode_id is None or progress_percent is None:
            return Response({"error": "episode_id and progress_percent are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            progress_percent = float(progress_percent)
        except (TypeError, ValueError):
            return Response({"error": "progress_percent must be a number"}, status=status.HTTP_400_BAD_REQUEST)

        episode = get_object_or_404(EpisodeModel, id=episode_id, comic=comic)

        # Optional denorm inputs; fallback if not provided
        comic_title = request.data.get('comic_title') or comic.title
        episode_label = request.data.get('episode_label') or f"Chapter {episode.episode_number}"
        cover_url = request.data.get('cover_url')
        if not cover_url:
            try:
                cover_url = comic.cover_image.url if comic.cover_image else ""
            except Exception:
                cover_url = ""

        _record_reading_progress_digital(
            user=user,
            comic=comic,
            episode=episode,
            progress_percent=progress_percent,
            comic_title=comic_title,
            episode_label=episode_label,
            cover_url=cover_url,
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)

    # --- Reading Activity: mark finished (Digital) ---
    @action(detail=True, methods=['post'], url_path='mark-finished')
    def mark_finished(self, request, pk=None):
        """
        Mark the comic as finished (100%). Keeps row to power 'Read Again'.
        """
        comic = self.get_object()
        _mark_finished_digital(request.user, comic)
        return Response({"ok": True}, status=status.HTTP_200_OK)

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

        # Implicit access creation on first entitled view + engagement bump
        if not locked and not has_access:
            try:
                _, created = EpisodeAccess.objects.get_or_create(
                    user=user,
                    episode=episode,
                    defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
                )
                # Bump reader count + streak only if we actually created the access now
                _bump_reader_on_new_access(user, created)
                has_access = True
            except Exception:
                # Fail-safe: still respond
                pass

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

        # Seed Reading Activity for Digital on viewable episode (5%)
        try:
            if not locked:
                _record_reading_progress_digital(
                    user=user,
                    comic=episode.comic,
                    episode=episode,
                    progress_percent=5.0,
                    comic_title=getattr(episode.comic, "title", ""),
                    episode_label=f"Chapter {getattr(episode, 'episode_number', '')}",
                )
        except Exception:
            pass

        return Response(payload, status=status.HTTP_200_OK)


# --- Reading Activity helpers (Digital) ---
FINISH_THRESHOLD = 95.0  # server-side completion rule


def _record_reading_progress_digital(
    user,
    comic: ComicModel,
    episode: EpisodeModel,
    progress_percent: float,
    comic_title: str = "",
    episode_label: str = "",
    cover_url: str = "",
):
    """
    Upsert a ReadingActivity row for this user+digital+comic.
    Safe to call multiple times (idempotent by user,type,comic_id).
    If user re-opens a finished comic and reports progress below FINISH_THRESHOLD,
    bring it back to in-progress by clearing finished_at.
    """
    try:
        comic_id_str = str(getattr(comic, "id", comic))
        episode_id_str = str(getattr(episode, "id", episode))

        ra, _ = ReadingActivity.objects.get_or_create(
            user=user,
            type="digital",
            comic_id=comic_id_str,
            defaults={"episode_id": episode_id_str},
        )

        ra.episode_id = episode_id_str

        # Clamp and apply progress
        p = max(0.0, min(100.0, float(progress_percent)))
        ra.progress_percent = p

        # Optional denorm fields
        if comic_title:
            ra.comic_title = comic_title
        if episode_label:
            ra.episode_label = episode_label
        if cover_url:
            ra.cover_url = cover_url

        # If user is reading again with < FINISH_THRESHOLD, make it in-progress again
        if p < FINISH_THRESHOLD:
            ra.finished_at = None

        # Auto-finish if threshold crossed
        if p >= FINISH_THRESHOLD and getattr(ra, "finished_at", None) is None:
            ra.finished_at = timezone.now()

        ra.save()
    except Exception as e:
        # Log visibly so we can see why write failed
        print("[DigitalActivity] Save failed:", repr(e))
        raise

def _mark_finished_digital(user, comic: ComicModel):
    """
    Mark a digital comic as finished (100%). Keeps row to power 'Read Again'.
    """
    try:
        comic_id_str = str(getattr(comic, "id", comic))
        ra, _ = ReadingActivity.objects.get_or_create(
            user=user,
            type="digital",
            comic_id=comic_id_str,
        )
        ra.progress_percent = 100.0
        if ra.finished_at is None:
            ra.finished_at = timezone.now()
        ra.save()
    except Exception:
        pass