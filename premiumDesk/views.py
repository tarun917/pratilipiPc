# premiumDesk/views.py
from rest_framework import viewsets, permissions, decorators, response, status
from django.utils import timezone

from .models import SubscriptionModel
from .serializers import SubscriptionSerializer


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Routes (via DefaultRouter under /api/premium/):
    - GET    /api/premium/subscribe/            → list current user's subscriptions
    - GET    /api/premium/subscribe/{id}/       → retrieve (not used by app)
    - GET    /api/premium/subscribe/active/     → { active: bool, subscription: obj|null }

    POST/PUT/PATCH/DELETE are intentionally disabled here to prevent
    creating subscriptions without verified payment. Creation is handled
    exclusively by paymentsDesk.VerifyPaymentView after Razorpay verification.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SubscriptionSerializer
    queryset = SubscriptionModel.objects.all()  # Required by DRF

    def get_queryset(self):
        # Only current user's subscriptions, newest first
        return (
            SubscriptionModel.objects
            .filter(user=self.request.user)
            .order_by('-start_date')
        )

    @decorators.action(detail=False, methods=['get'], url_path='active')
    def active(self, request):
        """
        Returns:
        { "active": true, "subscription": <SubscriptionSerializer> } if a current subscription exists
        else { "active": false, "subscription": null }
        """
        now = timezone.now()
        sub = (
            self.get_queryset()
            .filter(end_date__gte=now)
            .order_by('-end_date')
            .first()
        )
        if sub:
            return response.Response({
                "active": True,
                "subscription": self.get_serializer(sub).data
            })
        return response.Response({"active": False, "subscription": None})