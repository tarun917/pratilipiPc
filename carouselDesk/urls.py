from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CarouselItemViewSet

router = DefaultRouter()
router.register(r'fetch', CarouselItemViewSet, basename='carousel-fetch')

urlpatterns = router.urls