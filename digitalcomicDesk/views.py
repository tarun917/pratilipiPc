from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from .models import ComicModel, EpisodeModel, CommentModel
from .serializers import ComicSerializer, EpisodeSerializer, CommentSerializer
from profileDesk.models import CustomUser
from django.shortcuts import get_object_or_404

class DigitalComicViewSet(viewsets.ModelViewSet):
    queryset = ComicModel.objects.all()
    serializer_class = ComicSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        genre = request.query_params.get('genre', '')
        queryset = self.queryset
        if genre:
            queryset = queryset.filter(genre=genre)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        comic = self.get_object()
        episodes = EpisodeModel.objects.filter(comic=comic)
        return Response({
            'comic': self.get_serializer(comic).data,
            'episodes': EpisodeSerializer(episodes, many=True).data
        })

    @action(detail=True, methods=['post'])
    def unlock(self, request, pk=None):
        comic = self.get_object()
        user = request.user
        episode_id = request.data.get('episode_id')
        is_premium = user.subscriptionmodel_set.exists()
        if is_premium:
            # Premium: unlock all episodes for this comic
            EpisodeModel.objects.filter(comic=comic).update(is_locked=False)
            return Response({"message": "All episodes unlocked (premium)"}, status=status.HTTP_200_OK)
        if user.coin_count >= 50:
            if episode_id:
                episode = EpisodeModel.objects.filter(id=episode_id, comic=comic, is_locked=True).first()
            else:
                episode = EpisodeModel.objects.filter(comic=comic, is_locked=True).first()
            if episode:
                episode.is_locked = False
                episode.save()
                user.coin_count -= 50
                user.save()
                return Response({"message": "Episode unlocked"}, status=status.HTTP_200_OK)
            return Response({"error": "No locked episodes found"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "Insufficient coins or no subscription"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def rate(self, request, pk=None):
        comic = self.get_object()
        rating = request.data.get('rating', 0)
        if 1 <= rating <= 5:
            comic.rating = ((comic.rating * comic.rating_count) + rating) / (comic.rating_count + 1)
            comic.rating_count += 1
            comic.save()
            return Response({"rating": comic.rating}, status=status.HTTP_200_OK)
        return Response({"error": "Invalid rating"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def view(self, request, pk=None):
        comic = self.get_object()
        comic.view_count += 1
        comic.save()
        return Response({"view_count": comic.view_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        comic = self.get_object()
        comic.favourite_count += 1
        comic.save()
        return Response({"favourite_count": comic.favourite_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def comment(self, request, pk=None):
        comic = self.get_object()
        episode_id = request.data.get('episode_id')
        comment_text = request.data.get('comment_text')
        if episode_id and comment_text:
            episode = get_object_or_404(EpisodeModel, id=episode_id, comic=comic)
            comment = CommentModel.objects.create(episode=episode, user=request.user, comment_text=comment_text)
            return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)
        return Response({"error": "Episode ID and comment text required"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def commentlike(self, request, pk=None):
        comic = self.get_object()
        comment_id = request.data.get('comment_id')
        if comment_id:
            comment = get_object_or_404(CommentModel, id=comment_id, episode__comic=comic)
            comment.likes_count += 1
            comment.save()
            return Response({"likes_count": comment.likes_count}, status=status.HTTP_200_OK)
        return Response({"error": "Comment ID required"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        comic = self.get_object()
        comic.favourite_count += 1
        comic.save()
        return Response({"favourite_count": comic.favourite_count}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def favourite(self, request, pk=None):
        comic = self.get_object()
        return Response({"message": "Added to favourites"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='episodes')
    def create_episode(self, request, pk=None):
        comic = self.get_object()
        serializer = EpisodeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(comic=comic)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)