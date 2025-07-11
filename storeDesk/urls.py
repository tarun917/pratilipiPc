from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GenreViewSet, ComicViewSet, OrderViewSet, ReviewViewSet, WishlistViewSet, PromotionViewSet, NotificationPreferenceViewSet, RestockNotificationViewSet, RecommendationViewSet, NotificationViewSet

router = DefaultRouter()
router.register(r'genres', GenreViewSet)
router.register(r'comics', ComicViewSet)
router.register(r'orders', OrderViewSet)
router.register(r'reviews', ReviewViewSet)
router.register(r'wishlist', WishlistViewSet)
router.register(r'promotions', PromotionViewSet)
router.register(r'notifications/preferences', NotificationPreferenceViewSet)
router.register(r'notifications/restock', RestockNotificationViewSet)
router.register(r'recommendations', RecommendationViewSet, basename='recommendations')
router.register(r'notifications', NotificationViewSet, basename='user_notifications')  # Unique basename

urlpatterns = router.urls + [
    path('comics/<int:pk>/share-link/', ComicViewSet.as_view({'get': 'share_link'}), name='comic-share-link'),
]