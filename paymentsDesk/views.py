from django.shortcuts import render

# Create your views here.
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.conf import settings
from django.utils import timezone
import razorpay

from premiumDesk.serializers import SubscriptionSerializer, PLAN_PRICING
from premiumDesk.models import SubscriptionModel

class CreateOrderView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Body: { "plan": "3_month", "amount": <paise>, "currency": "INR" }
        Returns: { "order_id": "<rzp_order_xxx>", "amount": <paise>, "currency":"INR" }
        """
        user = request.user
        plan = request.data.get('plan')
        amount = request.data.get('amount')  # paise
        currency = request.data.get('currency', 'INR')

        if plan not in PLAN_PRICING:
            return Response({"detail": "Invalid plan"}, status=status.HTTP_400_BAD_REQUEST)

        # Validate server-side price
        expected_amount_paise = int(round(float(PLAN_PRICING[plan]['price']) * 100))
        if not isinstance(amount, int):
            try:
                amount = int(amount)
            except Exception:
                return Response({"detail": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

        if amount != expected_amount_paise:
            # For safety, override client-provided amount with server amount
            amount = expected_amount_paise

        # Optional: Prevent multiple active subscriptions
        now = timezone.now()
        if SubscriptionModel.objects.filter(user=user, end_date__gt=now).exists():
            return Response({"detail": "Active subscription exists"}, status=status.HTTP_409_CONFLICT)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # Create an order on Razorpay
        order_payload = {
            "amount": amount,
            "currency": currency,
            "receipt": f"sub-{user.id}-{plan}-{int(now.timestamp())}",
            "payment_capture": 1,
        }
        try:
            order = client.order.create(order_payload)
        except Exception as e:
            return Response({"detail": f"Failed to create order: {str(e)}"}, status=status.HTTP_502_BAD_GATEWAY)

        return Response({
            "order_id": order.get("id"),
            "amount": order.get("amount"),
            "currency": order.get("currency")
        }, status=status.HTTP_201_CREATED)


class VerifyPaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Body: {
          "plan": "3_month",
          "razorpay_payment_id": "...",
          "razorpay_order_id": "...",
          "razorpay_signature": "..."
        }
        On success: creates SubscriptionModel and returns SubscriptionSerializer data.
        """
        plan = request.data.get('plan')
        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')

        if plan not in PLAN_PRICING:
            return Response({"detail": "Invalid plan"}, status=status.HTTP_400_BAD_REQUEST)

        if not all([payment_id, order_id, signature]):
            return Response({"detail": "Missing payment verification fields"}, status=status.HTTP_400_BAD_REQUEST)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        # Verify signature
        try:
            client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
        except Exception as e:
            return Response({"detail": f"Signature verification failed: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        # Passed verification -> create subscription
        serializer = SubscriptionSerializer(data={"plan": plan}, context={"request": request})
        serializer.is_valid(raise_exception=True)
        subscription = serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)