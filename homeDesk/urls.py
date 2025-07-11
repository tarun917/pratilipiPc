from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import HomeContentViewSet

router = DefaultRouter()
router.register(r'content', HomeContentViewSet, basename='home-content')

urlpatterns = router.urls