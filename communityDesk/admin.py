from django.contrib import admin
from .models import Post, Comment, Poll, Vote, Follow, Like, UserEngagementStats


# Post
class PostAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'short_text', 'created_at', 'updated_at', 'share_count')
    search_fields = ('text', 'user__username')
    list_filter = ('created_at', 'user')
    readonly_fields = ('id', 'user', 'text', 'created_at', 'updated_at', 'share_count', 'commenting_enabled', 'hashtags')

    def short_text(self, obj):
        return (obj.text[:60] + '…') if len(obj.text) > 60 else obj.text
    short_text.short_description = 'Text'


# Comment
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'parent', 'short_text', 'created_at')
    search_fields = ('text', 'user__username', 'post__id')
    list_filter = ('created_at', 'user')
    readonly_fields = ('id', 'post', 'user', 'parent', 'text', 'created_at')

    def short_text(self, obj):
        return (obj.text[:60] + '…') if len(obj.text) > 60 else obj.text
    short_text.short_description = 'Text'


# Poll
class PollAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'question', 'created_at')
    search_fields = ('question', 'post__id')
    list_filter = ('created_at',)
    readonly_fields = ('id', 'post', 'question', 'created_at', 'options', 'votes')


# Vote
class VoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'poll', 'user', 'option_id', 'created_at')
    search_fields = ('user__username', 'poll__id', 'option_id')
    list_filter = ('created_at', 'user')
    readonly_fields = ('id', 'poll', 'user', 'option_id', 'created_at')


# Follow
class FollowAdmin(admin.ModelAdmin):
    list_display = ('id', 'follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')
    list_filter = ('created_at',)
    readonly_fields = ('id', 'follower', 'following', 'created_at')


# Like
class LikeAdmin(admin.ModelAdmin):
    list_display = ('id', 'post', 'user', 'created_at')
    search_fields = ('user__username', 'post__id')
    list_filter = ('created_at', 'user')
    readonly_fields = ('id', 'post', 'user', 'created_at')


# User Engagement Stats (Badges power)
class UserEngagementStatsAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'comic_read_count',
        'motion_watch_count',
        'streak_days',
        'last_activity_date',
        'updated_at',
    )
    search_fields = ('user__username',)
    list_filter = ('streak_days', 'last_activity_date')
    readonly_fields = ('updated_at',)
    ordering = ('-updated_at',)


# Register Models with Admin
admin.site.register(Post, PostAdmin)
admin.site.register(Comment, CommentAdmin)
admin.site.register(Poll, PollAdmin)
admin.site.register(Vote, VoteAdmin)
admin.site.register(Follow, FollowAdmin)
admin.site.register(Like, LikeAdmin)
admin.site.register(UserEngagementStats, UserEngagementStatsAdmin)