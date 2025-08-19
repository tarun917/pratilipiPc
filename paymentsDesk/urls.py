from django.urls import path
from .views import CreateOrderView, VerifyPaymentView

urlpatterns = [
    path('order/', CreateOrderView.as_view(), name='razorpay-create-order'),
    path('verify/', VerifyPaymentView.as_view(), name='razorpay-verify-payment'),
]