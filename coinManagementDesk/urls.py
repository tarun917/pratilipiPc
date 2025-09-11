from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import CoinViewSet, BalanceView

router = DefaultRouter()
# Read-only wallet viewset, scoped to current user
router.register(r'wallet', CoinViewSet, basename='wallet')

urlpatterns = [
    # GET /api/coins/balance/ -> {"balance": <int>}
    path('balance/', BalanceView.as_view(), name='coin-balance'),
] + router.urls