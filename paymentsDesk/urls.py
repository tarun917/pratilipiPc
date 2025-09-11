from django.urls import path
from .views import (
    CreateOrderView,
    VerifyPaymentView,
    RazorpayWebhookView,
    CheckoutOrderView,
)

urlpatterns = [
    # Premium (subscriptions) via Razorpay
    path('order/', CreateOrderView.as_view(), name='razorpay-create-order'),
    path('verify/', VerifyPaymentView.as_view(), name='razorpay-verify-payment'),

    # Webhook
    path('webhook/razorpay/', RazorpayWebhookView.as_view(), name='razorpay-webhook'),

    # Store checkout (physical goods)
    path('checkout/', CheckoutOrderView.as_view(), name='razorpay-store-checkout'),
]