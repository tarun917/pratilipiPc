import json
from rest_framework import serializers
from django.core.exceptions import ValidationError
import re

from profileDesk.serializers import ShortUserSerializer
from .models import Post, Comment, Poll, Vote, Follow, Like
from profileDesk.models import CustomUser

class PostSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False) # Allow user to be set automatically
    user = ShortUserSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    poll = serializers.SerializerMethodField()  # Show only first poll, if exists

    class Meta:
        model = Post
        fields = [
            'id', 'user', 'text', 'image_url', 'hashtags', 'commenting_enabled',
            'like_count', 'comment_count', 'is_liked', 'share_count', 'poll',
            'created_at', 'updated_at'
        ]
        extra_kwargs = {
            'image_url': {'required': False},
            'hashtags': {'required': False},
        }

    def get_like_count(self, obj):
        return Like.objects.filter(post=obj).count()

    def get_comment_count(self, obj):
        return Comment.objects.filter(post=obj).count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            return Like.objects.filter(post=obj, user=request.user).exists()
        return False

    def get_poll(self, obj):
        poll = Poll.objects.filter(post=obj).first()
        if poll:
            # Show my_vote also if user is authenticated
            poll_data = PollSerializer(poll).data
            request = self.context.get('request')
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                vote = Vote.objects.filter(poll=poll, user=request.user).first()
                poll_data['my_vote'] = vote.option_id if vote else None
            else:
                poll_data['my_vote'] = None
            return poll_data
        return None

    def validate_text(self, value):
        if not value.strip():
            raise ValidationError("Text cannot be empty.")
        if len(value) > 512:
            raise ValidationError("Text must not exceed 512 characters.")
        if not any(c.isalnum() for c in value):
            raise ValidationError("Text must contain at least one alphanumeric character.")
        return value

    def validate_hashtags(self, value):
        try:
            if value:
                # If value is a string (from form-data or dumped JSON), try to decode it as JSON
                if isinstance(value, str):
                    hashtags = json.loads(value) if value else []
                else:
                    hashtags = value
                if not all(isinstance(tag, str) and re.match(r'^#\w+$', tag) for tag in hashtags):
                    raise ValidationError("Hashtags must start with # and contain only letters, numbers, or underscores.")
            else:
                hashtags = []
            return hashtags  # Return the list for saving
        except json.JSONDecodeError:
            raise ValidationError("Hashtags must be valid JSON.")


    def validate_hashtags(self, value):
        try:
            if value:
            # If value is a string (from form-data), try to decode it as JSON
                if isinstance(value, str):
                    hashtags = json.loads(value) if value else []
            else:
                hashtags = value
            if not all(isinstance(tag, str) and re.match(r'^#\w+$', tag) for tag in hashtags):
                raise ValidationError("Hashtags must start with # and contain only letters, numbers, or underscores.")
            else:
                hashtags = []
            return hashtags  # Return the list for saving
        except json.JSONDecodeError:
            raise ValidationError("Hashtags must be valid JSON.")

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)  # Allow user to be set automatically
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), required=False)  # Allow post to be set automatically
    user = ShortUserSerializer(read_only=True)  # Nest user info

    class Meta:
        model = Comment
        fields = ['id', 'post', 'user', 'text', 'created_at']

    def validate_text(self, value):
        if not value.strip():
            raise ValidationError("Text cannot be empty.")
        if len(value) > 256:
            raise ValidationError("Text must not exceed 256 characters.")
        return value

class PollSerializer(serializers.ModelSerializer):
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), required=False)  # Allow post to be set automatically

    class Meta:
        model = Poll
        fields = ['id', 'post', 'question', 'options', 'votes', 'created_at']

    def validate_options(self, value):
        if not isinstance(value, dict) or len(value) < 2 or len(value) > 6:
            raise ValidationError("Options must be a dictionary with 2 to 6 entries.")
        return value

    def validate(self, data):
        if 'options' in data and 'votes' in data and set(data['votes'].keys()) != set(data['options'].keys()):
            raise ValidationError("Votes keys must match options keys.")
        return data

class VoteSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)  # Allow user to be set automatically)  
    poll = serializers.PrimaryKeyRelatedField(queryset=Poll.objects.all(), required=False)  # Allow poll to be set automatically

    class Meta:
        model = Vote
        fields = ['id', 'poll', 'user', 'option_id', 'created_at']
        extra_kwargs = {
            'option_id': {'required': True},
        }

    def validate_option_id(self, value):
        poll = self.context['request'].data.get('poll')
        if poll:
            poll_obj = Poll.objects.get(id=poll.id)
            if value not in poll_obj.options.keys():
                raise ValidationError("Invalid option ID.")
        return value

    def validate(self, data):
        if Vote.objects.filter(poll=data['poll'], user=data['user']).exists():
            raise ValidationError("You have already voted in this poll.")
        return data

class FollowSerializer(serializers.ModelSerializer):
    follower = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())
    following = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = Follow
        fields = ['id', 'follower', 'following', 'created_at']

    def validate(self, data):
        if data['follower'] == data['following']:
            raise ValidationError("You cannot follow yourself.")
        if Follow.objects.filter(follower=data['follower'], following=data['following']).exists():
            raise ValidationError("You are already following this user.")
        return data

class LikeSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)  # Allow user to be set automatically
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), required=False)  # Allow post to be set automatically

    class Meta:
        model = Like
        fields = ['id', 'post', 'user', 'created_at']

    def validate(self, data):
        if Like.objects.filter(post=data['post'], user=data['user']).exists():
            raise ValidationError("You have already liked this post.")
        return data