# views.py
import json
import logging
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action

from authDesk import serializers
from .models import Post, Comment, Poll, Vote, Follow, Like
from profileDesk.models import CustomUser
from .serializers import PostSerializer, CommentSerializer, PollSerializer, VoteSerializer, FollowSerializer, LikeSerializer
from django.shortcuts import get_object_or_404
from django.db.models import Q, Exists, OuterRef, Subquery
from rest_framework.pagination import PageNumberPagination
from django.views.decorators.cache import cache_page
from django.views.decorators import cache
from django.utils.decorators import method_decorator
from rest_framework.generics import ListAPIView
from profileDesk.serializers import SearchUserSerializer


logger = logging.getLogger(__name__)


class PostPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CommentPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all().order_by('-created_at')
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PostPagination  # Add pagination

    def get_queryset(self):
        qs = super().get_queryset().select_related('user')
        user = getattr(self.request, 'user', None)
        if user and user.is_authenticated:
            likes_qs = Like.objects.filter(post=OuterRef('pk'), user=user)
            qs = qs.annotate(
                is_liked=Exists(likes_qs),
                my_like_id=Subquery(likes_qs.values('id')[:1]),
            )
        return qs

    def perform_create(self, serializer):
        # Use validated hashtags from serializer
        hashtags = serializer.validated_data.get('hashtags', [])
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
    pagination_class = CommentPagination

    def get_queryset(self):
        post_id = self.kwargs['post_pk']
        parent_id = self.request.query_params.get('parent_id')
        qs = Comment.objects.filter(post_id=post_id).order_by('-created_at')
        if parent_id is not None and parent_id != '':
            return qs.filter(parent_id=parent_id)
        # Top-level only by default
        return qs.filter(parent__isnull=True)

    def perform_create(self, serializer):
        post = get_object_or_404(Post, pk=self.kwargs['post_pk'])
        if not post.commenting_enabled:
            # Using DRF pattern: raise error via response in create is clunky; better validate in serializer
            raise serializers.ValidationError({"error": "Commenting is disabled for this post."})
        # Handle parent reply (optional)
        parent_id = self.request.data.get('parent_id')
        parent = None
        if parent_id:
            parent = get_object_or_404(Comment, pk=parent_id)
            if parent.post_id != post.id:
                raise serializers.ValidationError({"error": "Parent comment must belong to the same post."})
        serializer.save(user=self.request.user, post=post, parent=parent)

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
        from rest_framework import serializers as drf_serializers

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
            return Response(
                {
                    "id": existing_vote.id,
                    "poll": poll.id,
                    "user": user.id,
                    "option_id": existing_vote.option_id,
                    "created_at": existing_vote.created_at
                },
                status=status.HTTP_200_OK
            )

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
        # For list, return who I follow
        if self.action == 'list':
            return Follow.objects.filter(follower=self.request.user)
        return Follow.objects.all()

    def create(self, request, *args, **kwargs):
        # Follow target user by URL param, ignore request body
        target_user = get_object_or_404(CustomUser, pk=self.kwargs.get('user_pk'))
        if target_user == request.user:
            return Response({"error": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        obj, created = Follow.objects.get_or_create(
            follower=request.user,
            following=target_user
        )
        data = FollowSerializer(obj).data
        return Response(data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=False, methods=['delete'], url_path='remove', url_name='remove')
    def remove(self, request, user_pk=None):
        # Unfollow target user by URL param, no follow-id needed
        target_user = get_object_or_404(CustomUser, pk=user_pk)
        deleted, _ = Follow.objects.filter(follower=request.user, following=target_user).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response({"error": "Not following."}, status=status.HTTP_404_NOT_FOUND)

    def follow_status(self, request, user_pk=None):
        target_user = get_object_or_404(CustomUser, pk=user_pk)
        rel = Follow.objects.filter(follower=request.user, following=target_user).values('id').first()
        return Response(
            {
            "is_following": bool(rel),
            "id": rel['id'] if rel else None
            },
            status=status.HTTP_200_OK
        )

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
        # List likes for current user (as per your earlier notes)
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