from django.utils import timezone
from django.db import transaction
from rest_framework import viewsets, permissions, decorators, response, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from profileDesk.models import CustomUser
from .models import SubscriptionModel, WalletLedger
from .serializers import (
    SubscriptionSerializer,
    CoinsConsumeSerializer,
    WalletLedgerSerializer,
)


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Routes (via DefaultRouter under /api/premium/):
    - GET    /api/premium/subscribe/           → list current user's subscriptions
    - GET    /api/premium/subscribe/{id}/      → retrieve (not used by app)
    - GET    /api/premium/subscribe/active/    → { active: bool, subscription: obj|null }

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
        else { "active": false, "subscription": None }
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


class CoinsConsumeView(APIView):
    """
    POST /api/premium/coins/consume/
    Body: { "amount": <int>, "reason": "<reason>", "idempotency_key": "<key>", "link_model"?: str, "link_id"?: str }

    - Authenticated users only.
    - Idempotent on idempotency_key:
        - If a ledger with the same idempotency_key already exists for this user, return that result (200).
        - If the key exists for a different user, return 409.
    - Atomic: debits coins and writes a WalletLedger row with balance snapshot.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        serializer = CoinsConsumeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        reason = serializer.validated_data["reason"]
        idempotency_key = serializer.validated_data["idempotency_key"]
        link_model = serializer.validated_data.get("link_model")
        link_id = serializer.validated_data.get("link_id")

        user = request.user

        # Idempotency check first
        existing = WalletLedger.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            if existing.user_id != user.id:
                return Response(
                    {"detail": "Idempotency key already used by another user"},
                    status=status.HTTP_409_CONFLICT,
                )
            # Return prior successful result
            return Response(
                {
                    "balance_after": existing.balance_after,
                    "ledger": WalletLedgerSerializer(existing).data,
                    "idempotent": True,
                },
                status=status.HTTP_200_OK,
            )

        # Lock user row to ensure consistent balance update
        user_locked = CustomUser.objects.select_for_update().get(id=user.id)

        if user_locked.coin_count is None:
            user_locked.coin_count = 0

        if user_locked.coin_count < amount:
            return Response(
                {"detail": "Insufficient balance", "balance": user_locked.coin_count},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_balance = user_locked.coin_count - amount

        # Create ledger and update balance atomically
        ledger = WalletLedger.objects.create(
            user=user_locked,
            delta=-amount,
            balance_after=new_balance,
            reason=reason,
            link_model=link_model or None,
            link_id=link_id or None,
            idempotency_key=idempotency_key,
        )

        user_locked.coin_count = new_balance
        user_locked.save(update_fields=["coin_count"])

        return Response(
            {
                "balance_after": new_balance,
                "ledger": WalletLedgerSerializer(ledger).data,
                "idempotent": False,
            },
            status=status.HTTP_201_CREATED,
        )