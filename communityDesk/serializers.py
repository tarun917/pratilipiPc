from rest_framework import serializers
from django.core.exceptions import ValidationError
import re
from .models import Post, Comment, Poll, Vote, Follow, Like
from profileDesk.models import CustomUser

class PostSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False) # Allow user to be set automatically

    class Meta:
        model = Post
        fields = ['id', 'user', 'text', 'image_url', 'hashtags', 'commenting_enabled', 'share_count', 'created_at', 'updated_at']
        extra_kwargs = {
            'image_url': {'required': False},
            'hashtags': {'required': False},
        }

    def validate_text(self, value):
        if not value.strip():
            raise ValidationError("Text cannot be empty.")
        if len(value) > 512:
            raise ValidationError("Text must not exceed 512 characters.")
        if not any(c.isalnum() for c in value):
            raise ValidationError("Text must contain at least one alphanumeric character.")
        return value

    def validate_image_url(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise ValidationError("Image size must not exceed 5MB.")
        if value and not value.name.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise ValidationError("Only JPG, JPEG, and PNG formats are allowed.")
        return value

    def validate_hashtags(self, value):
        if value and not all(re.match(r'^#\w+$', tag) for tag in value):
            raise ValidationError("Hashtags must start with # and contain only letters, numbers, or underscores.")
        return value

class CommentSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)  # Allow user to be set automatically
    post = serializers.PrimaryKeyRelatedField(queryset=Post.objects.all(), required=False)  # Allow post to be set automatically

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