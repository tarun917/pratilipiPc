from django.contrib import admin
from .models import Post, Comment, Poll, Vote, Follow, Like

# Custom Admin Classes
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'text', 'created_at', 'updated_at', 'share_count')
    search_fields = ('text', 'user__username')
    list_filter = ('created_at', 'user')
    readonly_fields = ('id', 'user', 'text', 'created_at', 'updated_at', 'share_count', 'commenting_enabled', 'hashtags')

class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'parent', 'text', 'created_at')
    search_fields = ('text', 'user__username', 'post__id')
    list_filter = ('created_at', 'user')
    readonly_fields = ('id', 'post', 'user', 'parent', 'text', 'created_at')

class PollAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'question', 'created_at')
    search_fields = ('question', 'post__id')
    list_filter = ('created_at',)
    readonly_fields = ('id', 'post', 'question', 'created_at', 'options', 'votes')

class VoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'poll', 'user', 'option_id', 'created_at')
    search_fields = ('user__username', 'poll__id', 'option_id')
    list_filter = ('created_at', 'user')
    readonly_fields = ('id', 'poll', 'user', 'option_id', 'created_at')

class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')
    list_filter = ('created_at',)
    readonly_fields = ('id', 'follower', 'following', 'created_at')

class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'created_at')
    search_fields = ('user__username', 'post__id')
    list_filter = ('created_at', 'user')
    readonly_fields = ('id', 'post', 'user', 'created_at')

# Register Models with Admin
admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Poll, PollAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Like, LikeAdmin)