from typing import Any, Dict, List
from django.apps import apps
from django.utils import timezone

def _safe_get_user_stats(user) -> Dict[str, int]:
    """
    Safely read engagement stats for this user. Returns zeros if not available.
    Expected keys:
      - comic_read_count
      - motion_watch_count
      - streak_days
    """
    stats = {
        "comic_read_count": 0,
        "motion_watch_count": 0,
        "streak_days": 0,
    }
    try:
        # Stats model lives in communityDesk
        StatsModel = apps.get_model('communityDesk', 'UserEngagementStats')
    except LookupError:
        StatsModel = None

    try:
        es = getattr(user, "engagement_stats", None)
        if not es and StatsModel is not None:
            es = StatsModel.objects.filter(user=user).first()
        if es:
            stats["comic_read_count"] = es.comic_read_count or 0
            stats["motion_watch_count"] = es.motion_watch_count or 0
            stats["streak_days"] = es.streak_days or 0
    except Exception:
        pass
    return stats

def _is_premium(user) -> bool:
    """
    Premium check sourced from premiumDesk active subscriptions.
    Fallback to CustomUser.is_premium if premiumDesk is unavailable.
    """
    try:
        SubscriptionModel = apps.get_model('premiumDesk', 'SubscriptionModel')
    except LookupError:
        SubscriptionModel = None

    if SubscriptionModel is not None:
        try:
            now = timezone.now()
            return SubscriptionModel.objects.filter(user=user, end_date__gte=now).exists()
        except Exception:
            return bool(getattr(user, "is_premium", False))
    return bool(getattr(user, "is_premium", False))

def build_badges_for_user(user) -> List[Dict[str, Any]]:
    """
    Compute badges for a user from engagement stats and flags.

    Returns a list of dicts like:
      { "type": "reader", "label": "Reader 100+", "level": 2 }
      { "type": "motion", "label": "Motion 300+", "level": 3 }
      { "type": "streak", "label": "Streak 13d", "level": 2 }
      { "type": "premium", "label": "Premium", "level": 1 }
    """
    stats = _safe_get_user_stats(user)
    badges: List[Dict[str, Any]] = []

    comic_count = int(stats.get("comic_read_count", 0) or 0)
    motion_count = int(stats.get("motion_watch_count", 0) or 0)
    streak_days = int(stats.get("streak_days", 0) or 0)

    # Reader tiers
    if comic_count >= 500:
        badges.append({"type": "reader", "label": "Reader 500+", "level": 3})
    elif comic_count >= 100:
        badges.append({"type": "reader", "label": "Reader 100+", "level": 2})
    elif comic_count >= 10:
        badges.append({"type": "reader", "label": "Reader 10+", "level": 1})

    # Motion/Watcher tiers
    if motion_count >= 300:
        badges.append({"type": "motion", "label": "Motion 300+", "level": 3})
    elif motion_count >= 100:
        badges.append({"type": "motion", "label": "Motion 100+", "level": 2})
    elif motion_count >= 10:
        badges.append({"type": "motion", "label": "Motion 10+", "level": 1})

    # Streak (3/7/30 level; label shows exact days)
    if streak_days >= 3:
        if streak_days >= 30:
            level = 3
        elif streak_days >= 7:
            level = 2
        else:
            level = 1
        badges.append({"type": "streak", "label": f"Streak {streak_days}d", "level": level})

    # Premium badge
    if _is_premium(user):
        badges.append({"type": "premium", "label": "Premium", "level": 1})

    return badges