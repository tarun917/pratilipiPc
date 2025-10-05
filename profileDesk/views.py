from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser

from django.apps import apps
from django.utils import timezone

from .models import CustomUser, Address
from .serializers import (
    CustomUserSerializer,
    ProfileUpdateSerializer,
    ProfileImageSerializer,
    AddressSerializer,
)

# Import Follow/Post for counts
from communityDesk.models import Follow, Post

# Shared badge utility (single source of truth used by Community and Profile)
from communityDesk.utils.badges import build_badges_for_user


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


class ProfileViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser,)

    def list(self, request):
        return Response({"error": "List view not allowed"}, status=status.HTTP_403_FORBIDDEN)

    def retrieve(self, request, pk=None):
        user = request.user

        profile_image_url = user.profile_image.url if user.profile_image else None
        if profile_image_url and not profile_image_url.startswith('http'):
            profile_image_url = request.build_absolute_uri(profile_image_url)

        # Compute counts
        followers_count = Follow.objects.filter(following=user).count()
        following_count = Follow.objects.filter(follower=user).count()

        # Compute badges via shared utility
        try:
            badges = build_badges_for_user(user)
        except Exception:
            badges = []

        # Fallback: ensure streak badge present if streak_days > 0
        es = _get_or_create_engagement(user)
        if es and (getattr(es, "streak_days", 0) or 0) > 0:
            # Only add if utility hasn't added it already
            has_streak = any(
                (isinstance(b, dict) and b.get("type", "").lower() == "streak")
                for b in badges
            )
            if not has_streak:
                badges.append({
                    "type": "streak",
                    "label": f"{es.streak_days}-day streak",
                    "days": es.streak_days,
                })

        return Response({
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "mobile_number": user.mobile_number,
            "profile_image": profile_image_url,
            "about": user.about,
            "coin_count": user.coin_count,
            "badge": user.badge,  # legacy (kept for backward-compat)
            "badges": badges,     # authoritative badges list (with streak fallback)
            "followers_count": followers_count,
            "following_count": following_count,
            "posts_count": Post.objects.filter(user=user).count(),
            "date_joined": user.date_joined,  # helpful frontend info
        }, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        user = request.user
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def upload_image(self, request):
        user = request.user
        serializer = ProfileImageSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='ping/active')
    def ping_active(self, request):
        """
        POST /api/profile/ping/active/
        Marks user as active today to maintain streak even without content completion.
        Response:
          { "status": "updated"|"already_marked_today"|"engagement_stats_unavailable"|"update_failed",
            "streak_days": <int>|null,
            "last_activity_date": "YYYY-MM-DD"|null }
        """
        ok, status_code = _touch_streak_today(request.user)
        es = _get_or_create_engagement(request.user)
        return Response({
            "status": status_code,
            "streak_days": getattr(es, "streak_days", None) if es else None,
            "last_activity_date": str(getattr(es, "last_activity_date", "")) if es else None
        }, status=status.HTTP_200_OK)


# Public user details by ID (read-only, limited fields)
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.IsAuthenticated]  # switch to AllowAny if you want truly public


class AddressViewSet(viewsets.ModelViewSet):
    """
    Owner-scoped address CRUD. Serializer attaches request.user on create.
    """
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-updated_at')

    def perform_destroy(self, instance):
        # Policy: allow delete (even if default). Client can set another default later.
        instance.delete()