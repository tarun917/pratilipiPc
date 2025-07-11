from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CoinViewSet

router = DefaultRouter()
router.register(r'update', CoinViewSet, basename='coin-update')

urlpatterns = router.urls