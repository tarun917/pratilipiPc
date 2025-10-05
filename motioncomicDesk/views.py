from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.apps import apps
from django.utils import timezone

from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from readingActivityDesk.models import ReadingActivity

from .models import ComicModel, EpisodeModel, CommentModel, EpisodeAccess
from .serializers import ComicSerializer, EpisodeSerializer, CommentSerializer

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
            return
        if last is None:
            es.streak_days = max(1, es.streak_days or 0)
        else:
            delta = (today - last).days
            if delta == 1:
                es.streak_days = (es.streak_days or 0) + 1
            else:
                es.streak_days = 1
        es.last_activity_date = today
    except Exception:
        pass

def _bump_motion_on_new_access(user, new_access_created: bool):
    """
    If we actually created a NEW EpisodeAccess just now, increment motion_watch_count
    and update streak safely.
    """
    if not new_access_created:
        return
    es = _get_or_create_engagement(user)
    if es is None:
        return
    try:
        es.motion_watch_count = (es.motion_watch_count or 0) + 1
        _bump_streak(es)
        es.save(update_fields=['motion_watch_count', 'streak_days', 'last_activity_date', 'updated_at'])
    except Exception:
        pass

class MotionComicViewSet(viewsets.ModelViewSet):
    """
    Routes:
    - GET /api/motioncomic/motioncomic/?genre=
    - GET /api/motioncomic/motioncomic/{comic_id}/details/
    - POST /api/motioncomic/motioncomic/{comic_id}/unlock/   body: { episode_id }
      Response:
        200 -> { unlocked: true, source: "PREMIUM" | "ALREADY", episode_id, balance? }
        201 -> { unlocked: true, source: "COINS", episode_id, balance }
        400 -> { error, code?: "insufficient_balance" }
    - Additional actions: rate, view, like, comment, commentlike, share, favourite, create_episode
    - NEW:
      - POST /api/motioncomic/motioncomic/{comic_id}/progress/
      - POST /api/motioncomic/motioncomic/{comic_id}/mark-finished/
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

        Dev-friendly:
        - If settings.DISABLE_MOTION_LOCKS is True, treat as ALREADY and do nothing.
        - If EpisodeAccess table is missing, fail-open (treat as unlocked).
        """
        comic = self.get_object()
        user = request.user
        episode_id = request.data.get('episode_id')

        # Validate episode
        episode = EpisodeModel.objects.filter(id=episode_id, comic=comic).first() if episode_id else None
        if not episode:
            return Response({"error": "Valid episode_id required for this comic"}, status=status.HTTP_400_BAD_REQUEST)

        # Dev bypass: disable locks entirely when flag is set
        if getattr(settings, 'DISABLE_MOTION_LOCKS', False):
            return Response({"unlocked": True, "source": "ALREADY", "episode_id": episode.id}, status=status.HTTP_200_OK)

        # Idempotency: already unlocked for this user (safe if table exists)
        try:
            if EpisodeAccess.objects.filter(user=user, episode=episode).exists():
                return Response({"unlocked": True, "source": "ALREADY", "episode_id": episode.id}, status=status.HTTP_200_OK)
        except Exception:
            # Table missing -> fail-open for dev
            return Response({"unlocked": True, "source": "ALREADY", "episode_id": episode.id}, status=status.HTTP_200_OK)

        # Safety guard: admin globally unlocked -> do not charge, mark as ALREADY
        if not episode.is_locked:
            try:
                _, created = EpisodeAccess.objects.get_or_create(
                    user=user, episode=episode, defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
                )
                _bump_motion_on_new_access(user, created)
            except Exception:
                pass
            return Response({"unlocked": True, "source": "ALREADY", "episode_id": episode.id}, status=status.HTTP_200_OK)

        # Premium or Free episode -> grant without coins
        if episode.is_free or self._is_user_premium(user):
            try:
                _, created = EpisodeAccess.objects.get_or_create(
                    user=user, episode=episode,
                    defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
                )
                _bump_motion_on_new_access(user, created)
            except Exception:
                pass
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
        try:
            with transaction.atomic():
                # Re-check idempotency inside tx
                try:
                    if EpisodeAccess.objects.select_for_update().filter(user=user, episode=episode).exists():
                        return Response({"unlocked": True, "source": "ALREADY", "episode_id": episode.id}, status=status.HTTP_200_OK)
                except Exception:
                    pass

                # Deduct simple balance (replace with WalletLedger when available)
                user.coin_count = balance - cost
                user.save(update_fields=['coin_count'])

                try:
                    _, created = EpisodeAccess.objects.get_or_create(user=user, episode=episode, defaults={'source': EpisodeAccess.SOURCE_COINS})
                    _bump_motion_on_new_access(user, created)
                except Exception:
                    pass
        except Exception:
            return Response({"error": "Unlock failed, please try again"}, status=status.HTTP_400_BAD_REQUEST)

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

    # --- Reading Activity: progress upsert (Motion) ---
    @action(detail=True, methods=['post'], url_path='progress')
    def progress(self, request, pk=None):
        """
        Upsert motion watching progress for this comic.
        Body:
          {
            "episode_id": "<uuid>",
            "progress_percent": 0..100,
            "position_ms": 0.. ,
            "comic_title": "...",        (optional)
            "episode_label": "...",      (optional)
            "cover_url": "https://..."   (optional)
          }
        """
        comic = self.get_object()
        user = request.user
        episode_id = request.data.get('episode_id')
        progress_percent = request.data.get('progress_percent')
        position_ms = request.data.get('position_ms')

        if episode_id is None or progress_percent is None:
            return Response({"error": "episode_id and progress_percent are required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            progress_percent = float(progress_percent)
        except (TypeError, ValueError):
            return Response({"error": "progress_percent must be a number"}, status=status.HTTP_400_BAD_REQUEST)

        # position_ms optional numeric
        try:
            if position_ms is not None:
                position_ms = int(position_ms)
        except (TypeError, ValueError):
            return Response({"error": "position_ms must be an integer"}, status=status.HTTP_400_BAD_REQUEST)

        episode = get_object_or_404(EpisodeModel, id=episode_id, comic=comic)

        comic_title = request.data.get('comic_title') or comic.title
        episode_label = request.data.get('episode_label') or f"Episode {episode.episode_number}"
        cover_url = request.data.get('cover_url')
        if not cover_url:
            try:
                cover_url = comic.cover_image.url if hasattr(comic, "cover_image") and comic.cover_image else ""
            except Exception:
                cover_url = ""

        _record_motion_progress(
            user=user,
            comic=comic,
            episode=episode,
            progress_percent=progress_percent,
            position_ms=position_ms,
            comic_title=comic_title,
            episode_label=episode_label,
            cover_url=cover_url,
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)

    # --- Reading Activity: mark finished (Motion) ---
    @action(detail=True, methods=['post'], url_path='mark-finished')
    def mark_finished(self, request, pk=None):
        """
        Mark the motion comic as finished (100%). Keeps row for 'Read Again'.
        """
        comic = self.get_object()
        _mark_finished_motion(request.user, comic)
        return Response({"ok": True}, status=status.HTTP_200_OK)

class EpisodeViewSet(mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    GET /api/motioncomic/motioncomic/episode/{id}/
    Returns single episode with per-user lock, prev/next, playback_url.
    Also implicitly creates EpisodeAccess for entitled users on first view
    so leaderboard/streak update immediately (no separate unlock needed).
    """
    queryset = EpisodeModel.objects.all()
    serializer_class = EpisodeSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        instance = self.get_object()

        # Determine if this episode should be locked for the user
        entitled = False
        try:
            if instance.is_free or not instance.is_locked:
                entitled = True
            else:
                has_access = EpisodeAccess.objects.filter(user=user, episode=instance).exists()
                if has_access:
                    entitled = True
                else:
                    if getattr(user, 'is_authenticated', False):
                        if getattr(user, 'is_premium', False):
                            entitled = True
                        elif hasattr(user, 'subscriptionmodel_set'):
                            try:
                                entitled = user.subscriptionmodel_set.exists()
                            except Exception:
                                entitled = False

            # Implicit EpisodeAccess creation on first entitled view + engagement bump
            if entitled:
                try:
                    _, created = EpisodeAccess.objects.get_or_create(
                        user=user,
                        episode=instance,
                        defaults={'source': EpisodeAccess.SOURCE_PREMIUM}
                    )
                    _bump_motion_on_new_access(user, created)
                except Exception:
                    # Ignore DB issues; still return episode payload
                    pass
        except Exception:
            # Defensive: never block retrieval on entitlement checks
            pass

        serializer = self.get_serializer(instance, context={'request': request})
        return Response(serializer.data)

# --- Reading Activity helpers (Motion) ---
FINISH_THRESHOLD = 95.0  # server-side completion rule

def _record_motion_progress(user, comic, episode, progress_percent, position_ms=None,
                            comic_title="", episode_label="", cover_url=""):
    try:
        comic_id_str = str(getattr(comic, "id", comic))
        episode_id_str = str(getattr(episode, "id", episode))
        ra, _ = ReadingActivity.objects.get_or_create(
            user=user, type="motion", comic_id=comic_id_str,
            defaults={"episode_id": episode_id_str},
        )
        ra.episode_id = episode_id_str
        p = max(0.0, min(100.0, float(progress_percent)))
        ra.progress_percent = p
        if position_ms is not None:
            ra.position_ms = position_ms
        if comic_title: ra.comic_title = comic_title
        if episode_label: ra.episode_label = episode_label
        if cover_url: ra.cover_url = cover_url

        # If user is watching again with < FINISH_THRESHOLD, make it in-progress again
        FINISH_THRESHOLD = 95.0
        if p < FINISH_THRESHOLD:
            ra.finished_at = None  # bring it back to in-progress

        if p >= FINISH_THRESHOLD and ra.finished_at is None:
            ra.finished_at = timezone.now()

        ra.save()
    except Exception:
        pass

def _mark_finished_motion(user, comic: ComicModel):
    """
    Mark a motion comic as finished (100%). Keeps row to power 'Read Again'.
    """
    try:
        ra, _ = ReadingActivity.objects.get_or_create(
            user=user,
            type="motion",
            comic_id=comic.id,
        )
        ra.progress_percent = 100.0
        if ra.finished_at is None:
            ra.finished_at = timezone.now()
        ra.save()
    except Exception:
        pass