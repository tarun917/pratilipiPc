from rest_framework.routers import DefaultRouter
from .views import CarouselItemViewSet

router = DefaultRouter()
# Final endpoint: /api/carousel/fetch/ (when included under path('api/carousel/', ...))
router.register(r'fetch', CarouselItemViewSet, basename='carousel-fetch')

urlpatterns = router.urls