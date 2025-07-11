from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet

router = DefaultRouter()
router.register(r'fetch', NotificationViewSet, basename='notification-fetch')

urlpatterns = router.urls