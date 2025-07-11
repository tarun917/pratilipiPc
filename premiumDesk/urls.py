from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SubscriptionViewSet

router = DefaultRouter()
router.register(r'subscribe', SubscriptionViewSet, basename='subscribe')

urlpatterns = router.urls