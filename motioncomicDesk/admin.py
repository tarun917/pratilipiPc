from django.contrib import admin
from .models import ComicModel, EpisodeModel, CommentModel, EpisodeAccess


def _blend_rating(user_avg: float, user_count: int, C: float = 5.0, m: int = 20) -> float:
    """
    Bayesian/blended rating used for display:
        score = (v/(v+m))*R + (m/(v+m))*C
    R = user_avg, v = user_count, C = editorial prior (5.0), m = prior weight (20)
    """
    try:
        v = max(0, int(user_count or 0))
        R = float(user_avg or 0.0)
        if v <= 0 and m <= 0:
            return 0.0
        return ((v / (v + m)) * R) + ((m / (v + m)) * C)
    except Exception:
        return float(user_avg or 0.0)


@admin.register(ComicModel)
class ComicAdmin(admin.ModelAdmin):
    # Show both DB aggregates and displayed blended rating
    list_display = (
        'title',
        'genre',
        'display_rating',   # blended (seeded 5 with 20 users)
        'rating',           # raw user average in DB
        'rating_count',     # raw user count in DB
        'view_count',
        'favourite_count',
    )
    search_fields = ('title', 'genre')
    list_filter = ('genre',)
    readonly_fields = ('rating', 'rating_count')

    def display_rating(self, obj):
        score = _blend_rating(obj.rating, obj.rating_count, C=5.0, m=20)
        return f"{score:.1f}"
    display_rating.short_description = "Displayed Rating (Blended)"
    # Order by raw rating field if admin sorts this column
    display_rating.admin_order_field = 'rating'


@admin.register(EpisodeModel)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ('comic', 'episode_number', 'is_free', 'coin_cost', 'is_locked', 'video_url', 'video_file')
    list_select_related = ('comic',)
    list_filter = ('comic', 'is_free', 'is_locked')
    search_fields = ('comic__title',)
    ordering = ('comic', 'episode_number')
    # Quality-of-life in admin:
    autocomplete_fields = ('comic',)


@admin.register(CommentModel)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('episode', 'user', 'comment_text', 'likes_count', 'timestamp')
    list_select_related = ('episode', 'user')
    search_fields = ('user__username', 'episode__comic__title', 'comment_text')
    ordering = ('-timestamp',)
    # QoL:
    autocomplete_fields = ('episode', 'user')


@admin.register(EpisodeAccess)
class EpisodeAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'episode', 'source', 'unlocked_at')
    list_select_related = ('user', 'episode')
    list_filter = ('source', 'episode__comic')
    search_fields = ('user__username', 'episode__comic__title')
    ordering = ('-unlocked_at',)
    # QoL:
    autocomplete_fields = ('user', 'episode')