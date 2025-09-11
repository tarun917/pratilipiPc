import json
import hmac
import hashlib
from decimal import Decimal, ROUND_HALF_UP

import razorpay
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from profileDesk.models import CustomUser
from .models import Payment
from premiumDesk.models import SubscriptionModel, WalletLedger
from premiumDesk.serializers import SubscriptionSerializer, PLAN_PRICING

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

# Optional: update store orders on webhook if app installed
try:
    from storeDesk.models import Order as StoreOrder
except Exception:
    StoreOrder = None


def _to_paise(amount_rupees: Decimal) -> int:
    # Razorpay needs integer paise; use Decimal for accuracy
    return int((amount_rupees * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


# -----------------------------
# Razorpay: Subscriptions (digital)
# -----------------------------

class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Body: { "plan": "3_month" }
        Server decides price from PLAN_PRICING; client amount is ignored.
        Returns: { "order_id": "<rzp_order_xxx>", "amount": <paise>, "currency": "INR", "key_id": "<...>" }
        """
        user = request.user
        plan = request.data.get('plan')
        currency = 'INR'

        # Validate plan
        if plan not in PLAN_PRICING:
            return Response({"detail": "Invalid plan"}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce one active subscription at a time
        now = timezone.now()
        if SubscriptionModel.objects.filter(user=user, end_date__gt=now).exists():
            return Response({"detail": "Active subscription exists"}, status=status.HTTP_409_CONFLICT)

        # Server-authoritative amount
        price_rupees = Decimal(str(PLAN_PRICING[plan]['price']))  # e.g., 349.00
        amount_paise = _to_paise(price_rupees)

        # Razorpay client
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        except Exception as e:
            return Response({"detail": f"Razorpay init failed: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        order_payload = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": f"sub-{user.id}-{plan}-{int(now.timestamp())}",
            "payment_capture": 1,
            "notes": {"plan": plan, "user_id": str(user.id)},
        }

        try:
            rzp_order = client.order.create(order_payload)
        except Exception as e:
            return Response({"detail": f"Failed to create order: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        # Persist Payment row (amount in rupees)
        Payment.objects.create(
            user=user,
            order_id=rzp_order.get("id"),
            amount=price_rupees,
            currency=rzp_order.get("currency", currency),
            status='created',
            provider='razorpay',
            plan=plan,
            notes=f"receipt={rzp_order.get('receipt')}",
        )

        return Response(
            {
                "order_id": rzp_order.get("id"),
                "amount": rzp_order.get("amount"),  # paise
                "currency": rzp_order.get("currency", currency),
                "key_id": settings.RAZORPAY_KEY_ID,
            },
            status=status.HTTP_201_CREATED,
        )


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Body:
        {
          "plan": "3_month",
          "razorpay_payment_id": "...",
          "razorpay_order_id": "...",
          "razorpay_signature": "..."
        }
        On success: creates SubscriptionModel and returns SubscriptionSerializer data.
        """
        user = request.user
        plan = request.data.get('plan')
        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')

        if plan not in PLAN_PRICING:
            return Response({"detail": "Invalid plan"}, status=status.HTTP_400_BAD_REQUEST)

        if not all([payment_id, order_id, signature]):
            return Response({"detail": "Missing payment verification fields"}, status=status.HTTP_400_BAD_REQUEST)

        # Lookup Payment (lock row for safe update)
        try:
            payment_row = Payment.objects.select_for_update().get(order_id=order_id, user=user, provider='razorpay')
        except Payment.DoesNotExist:
            return Response({"detail": "Payment order not found"}, status=status.HTTP_404_NOT_FOUND)

        # Idempotency: if already paid with same payment_id, return active subscription snapshot
        if payment_row.status == 'paid' and payment_row.payment_id == payment_id:
            active = SubscriptionModel.objects.filter(user=user, end_date__gte=timezone.now()).order_by('-end_date').first()
            if active:
                return Response(
                    {
                        "detail": "Already verified",
                        "subscription": SubscriptionSerializer(active).data,
                    },
                    status=status.HTTP_200_OK,
                )

        # Signature verification
        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
        except Exception as e:
            # Mark failed
            payment_row.status = 'failed'
            payment_row.payment_id = payment_id
            payment_row.notes = f"{(payment_row.notes or '')}\nverify_error={str(e)}"
            payment_row.save(update_fields=['status', 'payment_id', 'notes', 'updated_at'])
            return Response({"detail": f"Signature verification failed: {e}"}, status=status.HTTP_400_BAD_REQUEST)

        # Passed verification -> mark paid and create subscription
        payment_row.status = 'paid'
        payment_row.payment_id = payment_id
        payment_row.plan = plan
        payment_row.save(update_fields=['status', 'payment_id', 'plan', 'updated_at'])

        serializer = SubscriptionSerializer(data={"plan": plan}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class RazorpayWebhookView(APIView):
    """
    POST /api/payments/razorpay/webhook/razorpay/
    Header: X-Razorpay-Signature
    Body: raw JSON (Razorpay event)
    """
    permission_classes = [permissions.AllowAny]  # Razorpay hits unauthenticated

    def post(self, request):
        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", None)
        if not secret:
            return Response({"detail": "Webhook secret not configured"}, status=500)

        signature = request.headers.get("X-Razorpay-Signature")
        body = request.body or b""
        if not signature:
            return Response({"detail": "Missing signature"}, status=400)

        computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(computed, signature):
            return Response({"detail": "Invalid signature"}, status=400)

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            return Response({"detail": "Invalid JSON"}, status=400)

        event = payload.get("event")
        now = timezone.now()

        def set_paid(rzp_order_id: str | None, rzp_payment_id: str | None):
            if not rzp_order_id:
                return
            # Update Payment
            p = Payment.objects.filter(order_id=rzp_order_id, provider='razorpay').first()
            if p and p.status != "paid":
                p.status = "paid"
                if rzp_payment_id and not p.payment_id:
                    p.payment_id = rzp_payment_id
                p.save(update_fields=["status", "payment_id", "updated_at"])
            # Update Store order if present (physical flow)
            if StoreOrder is not None:
                o = StoreOrder.objects.filter(gateway_order_id=rzp_order_id).first()
                if o and o.payment_status != "paid":
                    o.payment_status = "paid"
                    o.fulfillment_status = "processing"
                    o.paid_at = now
                    if rzp_payment_id and not o.gateway_payment_id:
                        o.gateway_payment_id = rzp_payment_id
                    o.save(update_fields=["payment_status", "fulfillment_status", "paid_at", "gateway_payment_id", "updated_at"])

        def set_failed(rzp_order_id: str | None, rzp_payment_id: str | None):
            if not rzp_order_id:
                return
            p = Payment.objects.filter(order_id=rzp_order_id, provider='razorpay').first()
            if p and p.status not in ("paid", "failed"):
                p.status = "failed"
                if rzp_payment_id and not p.payment_id:
                    p.payment_id = rzp_payment_id
                p.save(update_fields=["status", "payment_id", "updated_at"])
            if StoreOrder is not None:
                o = StoreOrder.objects.filter(gateway_order_id=rzp_order_id).first()
                if o and o.payment_status not in ("paid", "failed"):
                    o.payment_status = "failed"
                    o.save(update_fields=["payment_status", "updated_at"])

        try:
            if event == "payment.captured":
                entity = (payload.get("payload") or {}).get("payment", {}).get("entity", {}) or {}
                set_paid(entity.get("order_id"), entity.get("id"))

            elif event == "payment.failed":
                entity = (payload.get("payload") or {}).get("payment", {}).get("entity", {}) or {}
                set_failed(entity.get("order_id"), entity.get("id"))

            elif event == "order.paid":
                entity = (payload.get("payload") or {}).get("order", {}).get("entity", {}) or {}
                rzp_order_id = entity.get("id")
                rzp_payment_id = None
                payments = entity.get("payments") or []
                if payments and isinstance(payments, list) and payments[0]:
                    rzp_payment_id = payments[0].get("id")
                set_paid(rzp_order_id, rzp_payment_id)

            # ignore other events
        except Exception as e:
            # Never fail webhook hard; respond 200 to prevent infinite retries
            return Response({"detail": "processed_with_warning", "error": str(e)}, status=200)

        return Response({"status": "ok"}, status=200)


# -----------------------------
# Razorpay: Store checkout (physical)
# -----------------------------

class CheckoutOrderView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        """
        Body: { "order_id": <int> }
        Creates a Razorpay order for the Store order's final_price.
        Returns: { "order_id", "amount"(paise), "currency", "key_id" }
        """
        # Ensure storeDesk available
        if StoreOrder is None:
            return Response({"detail": "Store module unavailable"}, status=501)

        user = request.user
        order_id = request.data.get("order_id")
        currency = "INR"

        if not order_id:
            return Response({"detail": "order_id required"}, status=400)

        try:
            order = StoreOrder.objects.select_for_update().get(id=order_id, user=user)
        except StoreOrder.DoesNotExist:
            return Response({"detail": "Order not found"}, status=404)

        if order.payment_status == "paid":
            return Response({"detail": "Order already paid"}, status=409)

        if order.final_price is None or Decimal(order.final_price) <= Decimal("0.00"):
            return Response({"detail": "Invalid final_price on order"}, status=400)

        try:
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        except Exception as e:
            return Response({"detail": f"Razorpay init failed: {e}"}, status=500)

        price_rupees = Decimal(order.final_price)
        amount_paise = _to_paise(price_rupees)

        # Idempotency: reuse existing pending gateway order
        if order.gateway == "razorpay" and order.gateway_order_id and order.payment_status == "pending":
            return Response(
                {
                    "order_id": order.gateway_order_id,
                    "amount": amount_paise,
                    "currency": currency,
                    "key_id": settings.RAZORPAY_KEY_ID,
                },
                status=200,
            )

        payload = {
            "amount": amount_paise,
            "currency": currency,
            "receipt": f"store-{order.id}-{int(timezone.now().timestamp())}",
            "payment_capture": 1,
            "notes": {"store_order_id": str(order.id), "user_id": str(user.id)},
        }

        try:
            rzp_order = client.order.create(payload)
        except Exception as e:
            return Response({"detail": f"Failed to create gateway order: {e}"}, status=502)

        order.gateway = "razorpay"
        order.gateway_order_id = rzp_order.get("id")
        order.amount = price_rupees
        order.save(update_fields=["gateway", "gateway_order_id", "amount", "updated_at"])

        return Response(
            {
                "order_id": rzp_order.get("id"),
                "amount": rzp_order.get("amount"),
                "currency": rzp_order.get("currency", currency),
                "key_id": settings.RAZORPAY_KEY_ID,
            },
            status=201,
        )


# -----------------------------
# Google Play Verification Flow
# -----------------------------

def _verify_play_purchase(token: str, package_name: str, product_id: str | None, subscription_id: str | None) -> tuple[bool, dict]:
    """
    Placeholder for Google Play Developer API verification.
    Returns (ok, details). Implement actual verification using Google API client.
    """
    gp_pkg = getattr(settings, "GOOGLE_PLAY_PACKAGE_NAME", None)
    if not gp_pkg or gp_pkg != package_name:
        return False, {"detail": "Invalid or missing Google Play package name"}

    # In production: validate token via Google Play Developer API
    if getattr(settings, "DEBUG", False):
        return True, {"purchaseState": 0, "acknowledged": True}

    return False, {"detail": "Google Play verification not configured"}


def _get_sku_maps():
    coin_map = getattr(settings, "COIN_PACK_SKUS", {}) or {}
    sub_map = getattr(settings, "SUB_PLAN_SKUS", {}) or {}
    return coin_map, sub_map


class PlayVerifyView(APIView):
    """
    POST /api/payments/play/verify/
    - Coins: { purchaseToken, productId, orderId?, purchaseTime?, obfuscatedAccountId? }
    - Subs:  { purchaseToken, subscriptionId, orderId?, purchaseTime?, obfuscatedAccountId? }

    Behavior:
    - Idempotent on purchaseToken.
    - Verifies token with Google Play (placeholder in DEBUG).
    - Coins: credits coins via WalletLedger (reason=play_credit).
    - Subs: creates/extends SubscriptionModel based on settings.SUB_PLAN_SKUS mapping.
    """
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        user = request.user
        purchase_token = request.data.get("purchaseToken")
        product_id = request.data.get("productId")
        subscription_id = request.data.get("subscriptionId")
        order_id = request.data.get("orderId")  # optional
        package_name = getattr(settings, "GOOGLE_PLAY_PACKAGE_NAME", None)

        if not purchase_token or (not product_id and not subscription_id):
            return Response({"detail": "purchaseToken and productId/subscriptionId required"}, status=400)

        # Verify with Google Play (placeholder respects DEBUG)
        ok, details = _verify_play_purchase(
            token=purchase_token,
            package_name=package_name,
            product_id=product_id,
            subscription_id=subscription_id,
        )
        if not ok:
            return Response(details, status=400)

        coin_map, sub_map = _get_sku_maps()
        print("DEBUG SUB_PLAN_SKUS keys:", list(sub_map.keys()))

        if product_id:
            # Coins flow
            if product_id not in coin_map:
                return Response({"detail": "Unknown productId"}, status=400)
            coins_added = int(coin_map[product_id])

            # Idempotency key for ledger
            idempotency_key = f"play:{purchase_token}"

            # Strong idempotency: ledger pre-check first (DB unique on idempotency_key)
            existing_ledger = WalletLedger.objects.filter(user=user, idempotency_key=idempotency_key).first()
            if existing_ledger:
                return Response(
                    {"detail": "Already verified", "balance_after": existing_ledger.balance_after},
                    status=200,
                )

            # Lock user and update balance
            user_locked = CustomUser.objects.select_for_update().get(id=user.id)
            current = int(user_locked.coin_count or 0)
            new_balance = current + coins_added

            WalletLedger.objects.create(
                user=user_locked,
                delta=coins_added,
                balance_after=new_balance,
                reason='play_credit',
                link_model='google_play',
                link_id=purchase_token[:64],
                idempotency_key=idempotency_key,
            )
            user_locked.coin_count = new_balance
            user_locked.save(update_fields=['coin_count'])

            # Payment row (idempotent by purchase_token unique)
            Payment.objects.update_or_create(
                user=user_locked,
                purchase_token=purchase_token,
                defaults={
                    "provider": "play",
                    "status": "paid",
                    "order_id": None,
                    "payment_id": None,
                    "amount": Decimal("0.00"),
                    "currency": "INR",
                    "plan": None,
                    "notes": f"productId={product_id};orderId={order_id or ''}",
                },
            )

            return Response(
                {"detail": "Coins credited", "coins_added": coins_added, "balance_after": new_balance},
                status=201,
            )

        else:
            # Subscription flow
            if subscription_id not in sub_map:
                return Response({"detail": "Unknown subscriptionId"}, status=400)
            mapped = sub_map[subscription_id]
            plan_key = mapped.get("plan")
            if not plan_key or plan_key not in PLAN_PRICING:
                return Response({"detail": "Invalid plan mapping"}, status=400)

            # Idempotency on Payment row
            existing = Payment.objects.filter(purchase_token=purchase_token, provider='play', user=user).first()
            if existing and existing.status == 'paid':
                active = SubscriptionModel.objects.filter(user=user, end_date__gte=timezone.now()).order_by('-end_date').first()
                if active:
                    return Response(
                        {"detail": "Already verified", "subscription": SubscriptionSerializer(active).data},
                        status=200,
                    )

            # Create/extend subscription
            serializer = SubscriptionSerializer(data={"plan": plan_key}, context={"request": request})
            serializer.is_valid(raise_exception=True)
            serializer.save()

            # Record Payment row
            Payment.objects.update_or_create(
                user=user,
                purchase_token=purchase_token,
                defaults={
                    "provider": "play",
                    "status": "paid",
                    "order_id": None,
                    "payment_id": None,
                    "amount": Decimal("0.00"),
                    "currency": "INR",
                    "plan": plan_key,
                    "notes": f"subscriptionId={subscription_id};orderId={order_id or ''}",
                },
            )

            return Response(
                {"detail": "Subscription granted", "subscription": serializer.data},
                status=201,
            )