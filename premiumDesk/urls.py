from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import SubscriptionViewSet, CoinsConsumeView

router = DefaultRouter()
router.register(r'subscribe', SubscriptionViewSet, basename='subscribe')

urlpatterns = [
    # Wallet/coins
    path('coins/consume/', CoinsConsumeView.as_view(), name='coins-consume'),
]

# Include router URLs after explicit paths
urlpatterns += router.urls