from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from .models import Genre, Comic, Order, Review, Wishlist, Promotion, NotificationPreference, RestockNotification
from .serializers import GenreSerializer, ComicSerializer, OrderSerializer, ReviewSerializer, WishlistSerializer, PromotionSerializer, NotificationPreferenceSerializer, RestockNotificationSerializer
from profileDesk.models import CustomUser
from django.core.cache import cache
from rest_framework.decorators import action
import boto3
from botocore.exceptions import NoCredentialsError

class StorePagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class GenreViewSet(viewsets.ModelViewSet):
    queryset = Genre.objects.all()
    serializer_class = GenreSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # No pagination for genres

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return Response(serializer.data)

class ComicViewSet(viewsets.ModelViewSet):
    queryset = Comic.objects.all()
    serializer_class = ComicSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StorePagination

    def get_queryset(self):
        queryset = self.queryset
        genre_ids = self.request.query_params.get('genre', '').split(',')
        if genre_ids and genre_ids[0]:
            queryset = queryset.filter(genres__id__in=genre_ids).distinct()
        search = self.request.query_params.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | Q(genres__name__icontains=search)
            ).distinct()
        sort = self.request.query_params.get('sort', 'created_at')
        if sort == 'price':
            queryset = queryset.order_by('price')
        elif sort == '-price':
            queryset = queryset.order_by('-price')
        elif sort == 'rating':
            queryset = queryset.order_by('-rating')
        elif sort == '-rating':
            queryset = queryset.order_by('rating')
        elif sort == 'newest':
            queryset = queryset.order_by('-created_at')
        filter_param = self.request.query_params.get('filter', '')
        if filter_param:
            if 'rating>4' in filter_param:
                queryset = queryset.filter(rating__gt=4)
            if 'stock>0' in filter_param:
                queryset = queryset.filter(stock_quantity__gt=0)
        return queryset

    def retrieve(self, request, pk=None):
        comic = get_object_or_404(Comic, pk=pk)
        serializer = self.get_serializer(comic)
        # Truncate description to 50 words
        words = serializer.data['description'].split()
        if len(words) > 50:
            serializer.data['description'] = ' '.join(words[:50]) + ' ...more'
        # Apply discount if promotion is active
        current_time = timezone.now()
        active_promotion = Promotion.objects.filter(
            genre=comic.genres.first(),  # First genre for simplicity
            start_date__lte=current_time,
            end_date__gte=current_time
        ).first()
        if active_promotion and comic.discount_price is None:
            discount = comic.price * (active_promotion.discount_percentage / 100)
            serializer.data['discount_price'] = max(0, comic.price - discount)
        # Generate signed URL for preview file (if exists)
        if comic.preview_file:
            s3_client = boto3.client('s3')
            try:
                preview_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': 'your-bucket-name', 'Key': comic.preview_file.name},
                    ExpiresIn=3600
                )
                serializer.data['preview_file'] = preview_url
            except NoCredentialsError:
                serializer.data['preview_file'] = None
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def share_link(self, request, pk=None):
        comic = get_object_or_404(Comic, pk=pk)
        base_url = request.build_absolute_uri('/')[:-1]
        link = f"{base_url}/api/store/comics/{comic.id}/"
        return Response({"share_link": link}, status=status.HTTP_200_OK)

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = 'order'

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        comic = serializer.validated_data['comic']
        if comic.stock_quantity <= 0:
            return Response({"error": "Comic is out of stock."}, status=status.HTTP_400_BAD_REQUEST)
        comic.stock_quantity -= 1
        comic.buyer_count += 1
        comic.save()
        serializer.save(user=self.request.user)

class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = 'review'

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        if not Order.objects.filter(user=self.request.user, comic=serializer.validated_data['comic']).exists():
            return Response({"error": "You can only review a comic you have purchased."}, status=status.HTTP_403_FORBIDDEN)
        review = serializer.save(user=self.request.user)
        comic = review.comic
        comic.rating_count += 1
        comic.rating = ((comic.rating * (comic.rating_count - 1)) + review.rating) / comic.rating_count
        comic.save()

class WishlistViewSet(viewsets.ModelViewSet):
    queryset = Wishlist.objects.all()
    serializer_class = WishlistSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = 'wishlist'

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
    
    def create(self, request, *args, **kwargs):
        comic_id = request.data.get('comic')
        comic = get_object_or_404(Comic, pk=comic_id)
        user = request.user
        if Wishlist.objects.filter(user=user, comic=comic).exists():
            Wishlist.objects.filter(user=user, comic=comic).delete()
            return Response({"message": "Removed from wishlist"}, status=status.HTTP_200_OK)
        serializer = self.get_serializer(data={'comic': comic_id})
        serializer.is_valid(raise_exception=True)
        serializer.save(user=user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StorePagination

    def get_queryset(self):
        return self.queryset.filter(end_date__gte=timezone.now())

class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = NotificationPreference.objects.all()
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class RestockNotificationViewSet(viewsets.ModelViewSet):
    queryset = RestockNotification.objects.all()
    serializer_class = RestockNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        comic = serializer.validated_data['comic']
        if comic.stock_quantity > 0:
            return Response({"error": "Comic is in stock, no notification needed."}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(user=self.request.user, notified=False)

    def trigger_restock_notification(self, user, comic):
        # Placeholder for Firebase notification
        print(f"Notification triggered for {user.username} - {comic.title} restocked")
        # Update notified status when implemented
        RestockNotification.objects.filter(user=user, comic=comic).update(notified=True)

class RecommendationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user
        cache_key = f'recommendations_{user.id}'
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(cached_data)

        purchased_orders = Order.objects.filter(user=user).prefetch_related('comic__genres')
        if purchased_orders.exists():
            genre_ids = set()
            for order in purchased_orders:
                genre_ids.update(genre.id for genre in order.comic.genres.all())  # Get all genre IDs
            # Fix: Recommend comics with any matching genre, exclude purchased ones
            all_comics = Comic.objects.filter(genres__id__in=genre_ids).distinct().order_by('-rating')
            purchased_comic_ids = Order.objects.filter(user=user).values_list('comic_id', flat=True)
            recommended_comics = [comic for comic in all_comics if comic.id not in purchased_comic_ids][:5]
            if not recommended_comics:  # Fallback if no new comics
                recommended_comics = [c for c in all_comics if c.id in purchased_comic_ids][:5]  # Recommend purchased
            serializer = ComicSerializer(recommended_comics, many=True)
            cache.set(cache_key, serializer.data, timeout=60*60)  # Cache for 1 hour
            return Response(serializer.data)
        return Response({"message": "No recommendations available"}, status=status.HTTP_200_OK)
    # [CHANGE END]

class NotificationViewSet(viewsets.ModelViewSet):
    queryset = RestockNotification.objects.all()
    serializer_class = RestockNotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user, notified=False)