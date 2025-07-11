from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DigitalComicViewSet

router = DefaultRouter()
router.register(r'digitalcomic', DigitalComicViewSet, basename='digitalcomic')

urlpatterns = router.urls