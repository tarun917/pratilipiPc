from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MotionComicViewSet

router = DefaultRouter()
router.register(r'motioncomic', MotionComicViewSet, basename='motioncomic')

urlpatterns = router.urls