import json
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Post, Comment, Poll, Vote, Follow, Like
from profileDesk.models import CustomUser
from .serializers import PostSerializer, CommentSerializer, PollSerializer, VoteSerializer, FollowSerializer, LikeSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from rest_framework.generics import ListAPIView
from profileDesk.serializers import SearchUserSerializer


logger = logging.getLogger(__name__)

class PostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PostPagination  # Add pagination

    def perform_create(self, serializer):
        # Process hashtags from form-data
        hashtags_input = self.request.data.get('hashtags', '')
        hashtags = []
        if hashtags_input:
            hashtags = [tag.strip() for tag in hashtags_input.split(',') if tag.strip().startswith('#') and tag.strip()[1:].replace('_', '').isalnum()]

        # Handle image upload
        if 'image' in self.request.FILES:
            serializer.save(user=self.request.user, image_url=self.request.FILES['image'], hashtags=hashtags)
        else:
            serializer.save(user=self.request.user, hashtags=hashtags)
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

    def get_queryset(self):
        return Comment.objects.filter(post_id=self.kwargs['post_pk'])

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs['post_pk'])
        if not post.commenting_enabled:
            return Response({"error": "Commenting is disabled for this post."}, status=status.HTTP_403_FORBIDDEN)
        serializer.save(user=self.request.user, post=post)

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
            return Response({"id": existing_vote.id, "poll": poll.id, "user": user.id, "option_id": existing_vote.option_id, "created_at": existing_vote.created_at}, status=status.HTTP_200_OK)

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
        if self.action == 'list':
            return Follow.objects.filter(follower=self.request.user)
        return Follow.objects.all()

    def perform_create(self, serializer):
        serializer.save(follower=self.request.user)

    def follow_status(self, request, user_pk=None):
        target_user = get_object_or_404(CustomUser, pk=user_pk)
        is_following = Follow.objects.filter(follower=request.user, following=target_user).exists()
        return Response({"is_following": is_following}, status=status.HTTP_200_OK)

    def followers(self, request, user_pk=None):
        target_user = get_object_or_404(CustomUser, pk=user_pk)
        followers = Follow.objects.filter(following=target_user).values_list('follower__username', flat=True)
        return Response({"followers": list(followers)}, status=status.HTTP_200_OK)

    def following(self, request, user_pk=None):
        target_user = get_object_or_404(CustomUser, pk=user_pk)
        following = Follow.objects.filter(follower=target_user).values_list('following__username', flat=True)
        return Response({"following": list(following)}, status=status.HTTP_200_OK)

class LikeViewSet(viewsets.ModelViewSet):
    queryset = Like.objects.all()
    serializer_class = LikeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
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



@method_decorator(cache_page(60*15), name='list')  # Cache for 15 minutes
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

        # Use proper serializers with context for 'is_liked' and 'is_following'
        posts_serialized = PostSerializer(posts, many=True, context={'request': request}).data
        users_serialized = SearchUserSerializer(users, many=True, context={'request': request}).data

        return Response({"posts": posts_serialized, "users": users_serialized}, status=status.HTTP_200_OK)
    

class UserPostsView(ListAPIView):
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PostPagination  # Already defined

    def get_queryset(self):
        user_id = self.kwargs.get('user_id')
        return Post.objects.filter(user__id=user_id).order_by('-created_at')