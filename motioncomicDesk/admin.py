from django.contrib import admin
from .models import ComicModel, EpisodeModel, CommentModel, EpisodeAccess


@admin.register(ComicModel)
class ComicAdmin(admin.ModelAdmin):
    list_display = ('title', 'genre', 'rating', 'view_count', 'favourite_count', 'rating_count')
    search_fields = ('title', 'genre')
    list_filter = ('genre',)


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