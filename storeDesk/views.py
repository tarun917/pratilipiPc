from decimal import Decimal
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.utils import timezone
from django.db import transaction

from .models import Genre, Comic, Order, Review, Wishlist, Promotion, PromotionRedemption
from .serializers import GenreSerializer, ComicSerializer, OrderSerializer, ReviewSerializer, WishlistSerializer, PromotionSerializer
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
    pagination_class = None

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
        # Truncate description
        words = serializer.data['description'].split()
        if len(words) > 50:
            serializer.data['description'] = ' '.join(words[:50]) + ' ...more'
        # Apply active promotion discount (genre-based) for display only
        current_time = timezone.now()
        active_promotion = Promotion.objects.filter(
            genre=comic.genres.first(),
            start_date__lte=current_time,
            end_date__gte=current_time
        ).first()
        if active_promotion and serializer.data.get('discount_price') in (None, ''):
            base = comic.discount_price if comic.discount_price else comic.price
            if active_promotion.discount_type == 'percentage':
                discount = (base * active_promotion.discount_value) / Decimal('100')
            else:
                discount = active_promotion.discount_value
            new_price = base - discount
            if new_price < 0:
                new_price = Decimal('0.00')
            serializer.data['discount_price'] = new_price
        # Signed preview URL
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

    @action(detail=True, methods=['get'], url_path='reviews')
    def reviews(self, request, pk=None):
        comic = get_object_or_404(Comic, pk=pk)
        queryset = Review.objects.filter(comic=comic).order_by('-created_at')
        paginator = StorePagination()
        page = paginator.paginate_queryset(queryset, request)
        serializer = ReviewSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    throttle_scope = 'order'

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        comic = serializer.validated_data['comic']
        if comic.stock_quantity <= 0:
            return Response({"error": "Comic is out of stock."}, status=status.HTTP_400_BAD_REQUEST)

        user = self.request.user
        # Base price honoring any existing discount_price
        base_price = comic.discount_price if comic.discount_price else comic.price
        discount = Decimal('0.00')
        promo_code_raw = self.request.data.get('promo_code', '')
        promo_code = promo_code_raw.strip().upper() if promo_code_raw else None

        if promo_code:
            now = timezone.now()
            promo = Promotion.objects.filter(code=promo_code, start_date__lte=now, end_date__gte=now).first()
            if not promo:
                return Response({"error": "Invalid or expired promo code."}, status=status.HTTP_400_BAD_REQUEST)

            # Applicability: if promo.comic set, must match; if promo.genre set, comic must be in genre
            if promo.comic and promo.comic_id != comic.id:
                return Response({"error": "Promo code not applicable for this comic."}, status=status.HTTP_400_BAD_REQUEST)
            if promo.genre and not comic.genres.filter(id=promo.genre_id).exists():
                return Response({"error": "Promo code not applicable for this genre."}, status=status.HTTP_400_BAD_REQUEST)

            # Usage limits
            if promo.max_uses is not None and promo.used_count >= promo.max_uses:
                return Response({"error": "Promo code usage limit reached."}, status=status.HTTP_400_BAD_REQUEST)
            if promo.per_user_limit is not None:
                user_used = PromotionRedemption.objects.filter(user=user, promotion=promo).count()
                if user_used >= promo.per_user_limit:
                    return Response({"error": "You have already used this promo code the maximum number of times."}, status=status.HTTP_400_BAD_REQUEST)

            # Minimum order amount
            if promo.min_order_amount and base_price < promo.min_order_amount:
                return Response({"error": "Order amount is below the minimum required for this promo."}, status=status.HTTP_400_BAD_REQUEST)

            # Compute discount
            if promo.discount_type == 'percentage':
                discount = (base_price * promo.discount_value) / Decimal('100')
            else:
                discount = promo.discount_value

            if discount < 0:
                discount = Decimal('0.00')
            if discount > base_price:
                discount = base_price

        final_price = base_price - discount
        if final_price < 0:
            final_price = Decimal('0.00')

        # Update stock & buyer count
        comic.stock_quantity -= 1
        comic.buyer_count += 1
        comic.save()

        # Save order
        order = serializer.save(
            user=user,
            promo_code=promo_code,
            discount_applied=discount,
            final_price=final_price
        )

        # Record redemption
        if promo_code:
            promo.used_count = (promo.used_count or 0) + 1
            promo.save(update_fields=['used_count'])
            PromotionRedemption.objects.create(user=user, promotion=promo, order=order)


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


# Notification-related viewsets removed because corresponding models do not exist in storeDesk.models


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
                genre_ids.update(genre.id for genre in order.comic.genres.all())
            all_comics = Comic.objects.filter(genres__id__in=genre_ids).distinct().order_by('-rating')
            purchased_comic_ids = Order.objects.filter(user=user).values_list('comic_id', flat=True)
            recommended_comics = [comic for comic in all_comics if comic.id not in purchased_comic_ids][:5]
            if not recommended_comics:
                recommended_comics = [c for c in all_comics if c.id in purchased_comic_ids][:5]
            serializer = ComicSerializer(recommended_comics, many=True)
            cache.set(cache_key, serializer.data, timeout=60 * 60)
            return Response(serializer.data)
        return Response({"message": "No recommendations available"}, status=status.HTTP_200_OK)


# NotificationViewSet removed because RestockNotification model/serializer not present