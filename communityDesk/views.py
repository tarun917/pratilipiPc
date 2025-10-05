import logging
from django.shortcuts import get_object_or_404
from django.db.models import Q, Exists, OuterRef, Subquery
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.apps import apps  # for dynamic model lookup
from django.utils import timezone  # used by streak helper

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView

from authDesk import serializers
from profileDesk.models import CustomUser
from .models import Post, Comment, Poll, Vote, Follow, Like
from .serializers import (
    PostSerializer,
    CommentSerializer,
    PollSerializer,
    VoteSerializer,
    FollowSerializer,
    LikeSerializer,
    CommunityUserSerializer,  # author/user DTO with my_follow_id + badges
)

logger = logging.getLogger(__name__)


# ================
# Streak utilities
# ================

def _get_or_create_engagement(user):
    """
    Get/create communityDesk.UserEngagementStats for the user (safe).
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


def _touch_streak_today(user):
    """
    Maintain streak_days and last_activity_date for 'daily active ping'.
    Rules:
    - If already today -> no change
    - If yesterday -> streak_days += 1
    - Else -> streak_days = 1
    """
    es = _get_or_create_engagement(user)
    if es is None:
        return False, "engagement_stats_unavailable"
    try:
        today = timezone.localdate()
        last = es.last_activity_date
        if last == today:
            return True, "already_marked_today"
        if last is None:
            es.streak_days = max(1, es.streak_days or 0)
        else:
            delta = (today - last).days
            if delta == 1:
                es.streak_days = (es.streak_days or 0) + 1
            else:
                es.streak_days = 1
        es.last_activity_date = today
        es.save(update_fields=["streak_days", "last_activity_date", "updated_at"])
        return True, "updated"
    except Exception:
        return False, "update_failed"


class PostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CommentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class UserPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PostPagination  # Add pagination

    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated:
            likes_qs = Like.objects.filter(post=OuterRef('pk'), user=user)
            qs = qs.annotate(
                is_liked=Exists(likes_qs),
                my_like_id=Subquery(likes_qs.values('id')[:1]),
            )
        return qs

    def perform_create(self, serializer):
        # Use validated hashtags from serializer
        hashtags = serializer.validated_data.get('hashtags', [])
        # Handle image upload
        if 'image' in self.request.FILES:
            serializer.save(user=self.request.user, image_url=self.request.FILES['image'], hashtags=hashtags)
        else:
            serializer.save(user=self.request.user, hashtags=hashtags)

        # Touch the author's streak today so badges remain fresh in Community as well
        try:
            _touch_streak_today(self.request.user)
        except Exception:
            logger.warning("Failed to touch streak for user=%s on post create", self.request.user.id, exc_info=True)

        logger.info(f"Post created by {self.request.user.username} with hashtags: {hashtags}")

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"error": "You can only update your own posts."}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"error": "You can only delete your own posts."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def share(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.share_count += 1
        instance.save()
        return Response({"message": "Post shared successfully", "share_count": instance.share_count}, status=status.HTTP_200_OK)

    def copy_link(self, request, *args, **kwargs):
        instance = self.get_object()
        base_url = request.build_absolute_uri('/')[:-1]  # Get base URL
        link = f"{base_url}/api/community/posts/{instance.id}/"
        return Response({"link": link}, status=status.HTTP_200_OK)


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommentPagination

    def get_queryset(self):
        post_id = self.kwargs['post_pk']
        parent_id = self.request.query_params.get('parent_id')
        qs = Comment.objects.filter(post_id=post_id).order_by('-created_at')
        if parent_id is not None and parent_id != '':
            return qs.filter(parent_id=parent_id)
        # Top-level only by default
        return qs.filter(parent__isnull=True)

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs['post_pk'])
        if not post.commenting_enabled:
            # Using DRF pattern: raise error via response in create is clunky; better validate in serializer
            raise serializers.ValidationError({"error": "Commenting is disabled for this post."})
        # Handle parent reply (optional)
        parent_id = self.request.data.get('parent_id')
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id)
            if parent.post_id != post.id:
                raise serializers.ValidationError({"error": "Parent comment must belong to the same post."})
        serializer.save(user=self.request.user, post=post, parent=parent)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({"error": "You can only delete your own comments."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class PollViewSet(viewsets.ModelViewSet):
    queryset = Poll.objects.all()
    serializer_class = PollSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Poll.objects.filter(post_id=self.kwargs['post_pk'])

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs['post_pk'])
        serializer.save(post=post)


class VoteViewSet(viewsets.ModelViewSet):
    queryset = Vote.objects.all()
    serializer_class = VoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Vote.objects.filter(poll_id=self.kwargs['poll_pk'])

    def create(self, request, *args, **kwargs):
        from rest_framework import serializers as drf_serializers

        poll = get_object_or_404(Poll, pk=self.kwargs['poll_pk'])
        user = request.user

        # Prepare data with poll and user
        data = request.data.copy()
        data['poll'] = poll.id
        data['user'] = user.id

        # Check and update existing vote
        existing_vote = Vote.objects.filter(poll=poll, user=user).first()
        if existing_vote:
            old_option_id = existing_vote.option_id
            if old_option_id == request.data.get('option_id'):
                return Response({"error": "You have already voted for this option."}, status=status.HTTP_400_BAD_REQUEST)
            poll.votes[old_option_id] = max(0, poll.votes.get(old_option_id, 0) - 1)  # Avoid negative votes
            existing_vote.option_id = request.data.get('option_id')
            existing_vote.save()
            poll.votes[request.data.get('option_id')] = poll.votes.get(request.data.get('option_id'), 0) + 1
            poll.save()
            return Response(
                {
                    "id": existing_vote.id,
                    "poll": poll.id,
                    "user": user.id,
                    "option_id": existing_vote.option_id,
                    "created_at": existing_vote.created_at
                },
                status=status.HTTP_200_OK
            )

        # Create new vote
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        vote = serializer.save(user=user, poll=poll)
        poll.votes[request.data.get('option_id')] = poll.votes.get(request.data.get('option_id'), 0) + 1
        poll.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class FollowViewSet(viewsets.ModelViewSet):
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # For list, return who I follow
        if self.action == 'list':
            return Follow.objects.filter(follower=self.request.user)
        return Follow.objects.all()

    def create(self, request, *args, **kwargs):
        # Follow target user by URL param, ignore request body
        target_user = get_object_or_404(CustomUser, pk=self.kwargs.get('user_pk'))
        if target_user == request.user:
            return Response({"error": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = Follow.objects.get_or_create(
            follower=request.user,
            following=target_user
        )
        data = FollowSerializer(obj).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='remove', url_name='remove')
    def remove(self, request, user_pk=None):
        # Unfollow target user by URL param, no follow-id needed
        target_user = get_object_or_404(CustomUser, pk=user_pk)
        deleted, _ = Follow.objects.filter(follower=self.request.user, following=target_user).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Not following."}, status=status.HTTP_404_NOT_FOUND)

    def follow_status(self, request, user_pk=None):
        target_user = get_object_or_404(CustomUser, pk=user_pk)
        rel = Follow.objects.filter(follower=self.request.user, following=target_user).values('id').first()
        return Response(
            {
                "is_following": bool(rel),
                "id": rel['id'] if rel else None
            },
            status=status.HTTP_200_OK
        )

    def followers(self, request, user_pk=None):
        """
        GET /api/community/users/{user_pk}/followers/
        Returns paginated list of users who follow {user_pk}, with my_follow_id relative to request.user
        """
        target_user = get_object_or_404(CustomUser, pk=user_pk)
        qs = CustomUser.objects.filter(
            id__in=Follow.objects.filter(following=target_user).values('follower_id')
        ).order_by('username')
        paginator = UserPagination()
        page = paginator.paginate_queryset(qs, request)
        data = CommunityUserSerializer(page, many=True, context={'request': request}).data
        return paginator.get_paginated_response(data)

    def following(self, request, user_pk=None):
        """
        GET /api/community/users/{user_pk}/following/
        Returns paginated list of users whom {user_pk} follows, with my_follow_id relative to request.user
        """
        target_user = get_object_or_404(CustomUser, pk=user_pk)
        qs = CustomUser.objects.filter(
            id__in=Follow.objects.filter(follower=target_user).values('following_id')
        ).order_by('username')
        paginator = UserPagination()
        page = paginator.paginate_queryset(qs, request)
        data = CommunityUserSerializer(page, many=True, context={'request': request}).data
        return paginator.get_paginated_response(data)


class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all()
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # List likes for current user (as per your earlier notes)
        return Like.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        post = get_object_or_404(Post, pk=self.kwargs['post_pk'])
        user = request.user

        # Check for duplicate like before creating
        if Like.objects.filter(post=post, user=user).exists():
            return Response({"error": "You have already liked this post."}, status=status.HTTP_400_BAD_REQUEST)

        # Prepare data with post and user
        data = request.data.copy()
        data['post'] = post.id
        data['user'] = user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(cache_page(60 * 15), name='list')  # Cache for 15 minutes
class SearchViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        query = request.query_params.get('q', '')
        posts = Post.objects.filter(
            Q(text__icontains=query) | Q(hashtags__icontains=query)
        )
        users = CustomUser.objects.filter(
            Q(username__icontains=query) | Q(full_name__icontains=query)
        )

        # Use proper serializers with context for 'is_liked' and 'my_follow_id'
        posts_serialized = PostSerializer(posts, many=True, context={'request': request}).data
        # Prefer community-aware serializer so UI gets my_follow_id on users
        users_serialized = CommunityUserSerializer(users, many=True, context={'request': request}).data

        return Response({"posts": posts_serialized, "users": users_serialized}, status=status.HTTP_200_OK)


class UserPostsView(ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PostPagination  # Already defined

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return Post.objects.filter(user__id=user_id).order_by('-created_at')


# =========================
# Leaderboard Implementation
# =========================

class LeaderboardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


def _leaderboard_score(user: CustomUser):
    """
    Hybrid scoring to preserve legacy big totals while uplifting new activity:
    1) Prefer engagement_stats totals (legacy scale) if present:
         reader = comic_read_count
         motion = motion_watch_count
         streak = streak_days
    2) Else fallback to EpisodeAccess-derived counts and inferred streak.

    Also compute has_activity from EpisodeAccess (read/watch/streak >= 1),
    so a new user who just acted gets uplift in zero-score ties even if
    engagement_stats haven’t updated yet.

    Weights:
      - Reader: 1.0
      - Motion: 1.2
      - Streak: 0.5

    Premium does NOT add score; it is used only as final tie-breaker.
    Returns (score, reader, motion, streak, is_premium, has_activity)
    """
    from datetime import timedelta
    from django.utils import timezone

    # ---------- Try engagement_stats first ----------
    reader = 0
    motion = 0
    streak = 0
    used_engagement_stats = False

    StatsModel = None
    try:
        # FIX: This model lives in communityDesk
        StatsModel = apps.get_model('communityDesk', 'UserEngagementStats')
    except LookupError:
        StatsModel = None

    stats_obj = None
    try:
        if StatsModel is not None:
            # Common relation name
            stats_obj = getattr(user, 'engagement_stats', None)
            if stats_obj is None:
                stats_obj = StatsModel.objects.filter(user=user).first()
        else:
            stats_obj = getattr(user, 'engagement_stats', None)
    except Exception:
        stats_obj = None

    if stats_obj is not None:
        try:
            reader = int(getattr(stats_obj, 'comic_read_count', 0) or 0)
            motion = int(getattr(stats_obj, 'motion_watch_count', 0) or 0)
            streak = int(getattr(stats_obj, 'streak_days', 0) or 0)
            used_engagement_stats = True
        except Exception:
            reader = motion = streak = 0
            used_engagement_stats = False

    # ---------- Gather EpisodeAccess activity for has_activity AND fallback ----------
    active_dates = set()
    ep_reader = 0
    ep_motion = 0

    # Digital: EpisodeAccess from digitalcomicDesk
    try:
        DigitalAccess = apps.get_model('digitalcomicDesk', 'EpisodeAccess')
    except LookupError:
        DigitalAccess = None

    if DigitalAccess is not None:
        try:
            ep_reader = DigitalAccess.objects.filter(user=user).count()
            for dt in DigitalAccess.objects.filter(user=user).values_list('unlocked_at', flat=True):
                if dt:
                    active_dates.add(dt.astimezone(timezone.get_current_timezone()).date())
        except Exception:
            ep_reader = 0

    # Motion: EpisodeAccess from motionDesk
    try:
        MotionAccess = apps.get_model('motionDesk', 'EpisodeAccess')
    except LookupError:
        MotionAccess = None

    if MotionAccess is not None:
        try:
            ep_motion = MotionAccess.objects.filter(user=user).count()
            for dt in MotionAccess.objects.filter(user=user).values_list('unlocked_at', flat=True):
                if dt:
                    active_dates.add(dt.astimezone(timezone.get_current_timezone()).date())
        except Exception:
            ep_motion = 0

    # Streak from EpisodeAccess dates (for fallback and has_activity)
    today = timezone.localdate()
    ep_streak = 0
    for i in range(0, 60):  # sane cap
        d = today - timedelta(days=i)
        if d in active_dates:
            ep_streak += 1
        else:
            break

    # If engagement_stats missing, fallback to EpisodeAccess-derived counts
    if not used_engagement_stats:
        reader = ep_reader
        motion = ep_motion
        streak = ep_streak

    # ---------- Premium (subscription-based) ----------
    try:
        SubscriptionModel = apps.get_model('premiumDesk', 'SubscriptionModel')
    except LookupError:
        SubscriptionModel = None

    if SubscriptionModel is not None:
        try:
            is_premium = SubscriptionModel.objects.filter(user=user, end_date__gte=timezone.now()).exists()
        except Exception:
            is_premium = bool(getattr(user, "is_premium", False))
    else:
        is_premium = bool(getattr(user, "is_premium", False))

    has_activity = 1 if (ep_reader > 0 or ep_motion > 0 or ep_streak > 0) else 0
    score = (reader * 1.0) + (motion * 1.2) + (streak * 0.5)
    return score, reader, motion, streak, is_premium, has_activity


class LeaderboardViewSet(viewsets.ViewSet):
    """
    GET /api/community/leaderboard/?window=all|month|week&page=1

    For now, 'month' and 'week' fallback to all-time until windowed stats are implemented.
    Returns paginated:
    {
      "count": ...,
      "next": ...,
      "previous": ...,
      "results": [
        { "user": <CommunityUserSerializer payload>, "score": 862.0, "rank": 1 }
      ]
    }
    """
    permission_classes = [IsAuthenticated]
    pagination_class = LeaderboardPagination

    def list(self, request):
        window = (request.query_params.get('window') or 'all').lower().strip()
        # Future: filter or switch to windowed stats here
        if window not in ('all', 'month', 'week'):
            window = 'all'

        # Fetch users; if you want to exclude staff/moderators, filter here
        users_qs = CustomUser.objects.all()

        # Build entries with score and tie-breakers
        entries = []
        for u in users_qs:
            score, reader, motion, streak, is_premium, has_activity = _leaderboard_score(u)
            entries.append({
                "user_obj": u,
                "score": float(score),
                "reader": reader,
                "motion": motion,
                "streak": streak,
                "has_activity": has_activity,
                "is_premium": is_premium,
            })

        # Sort:
        #  1) score desc
        #  2) streak desc
        #  3) motion desc
        #  4) reader desc
        #  5) has_activity desc (ensures 1+ action beats true-zero ties)
        #  6) premium desc (last tie-break)
        entries.sort(
            key=lambda e: (
                e["score"],
                e["streak"],
                e["motion"],
                e["reader"],
                e["has_activity"],
                1 if e["is_premium"] else 0,
            ),
            reverse=True
        )

        # Assign rank (1-based)
        for idx, e in enumerate(entries):
            e["rank"] = idx + 1

        # Paginate the list
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(entries, request)

        # Serialize user payloads
        results = []
        for e in page:
            user_payload = CommunityUserSerializer(e["user_obj"], context={'request': request}).data
            results.append({
                "user": user_payload,
                "score": e["score"],
                "rank": e["rank"],
            })

        return paginator.get_paginated_response(results)