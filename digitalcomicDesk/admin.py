from django.contrib import admin
from .models import ComicModel, EpisodeModel, CommentModel

@admin.register(ComicModel)
class ComicAdmin(admin.ModelAdmin):
    list_display = ('title', 'genre', 'rating', 'view_count', 'favourite_count')

@admin.register(EpisodeModel)
class EpisodeAdmin(admin.ModelAdmin):
    list_display = ('comic', 'episode_number', 'is_free', 'is_locked')

@admin.register(CommentModel)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('episode', 'user', 'comment_text', 'likes_count')