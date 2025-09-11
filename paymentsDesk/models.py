from django.db import models
from profileDesk.models import CustomUser  # Use your actual user model


class Payment(models.Model):
    PROVIDER_CHOICES = [
        ('razorpay', 'Razorpay'),
        ('play', 'Google Play'),
    ]

    STATUS_CHOICES = [
        ('created', 'Created'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments')

    # Razorpay: order_id is required; Play: allow NULL
    order_id = models.CharField(max_length=100, unique=True, blank=True, null=True)

    # Razorpay payment id (optional)
    payment_id = models.CharField(max_length=100, blank=True, null=True)

    # Google Play idempotency: purchase token (unique when present)
    purchase_token = models.CharField(max_length=200, unique=True, blank=True, null=True)

    amount = models.DecimalField(max_digits=10, decimal_places=2)  # in INR rupees; use 0.00 when unknown
    currency = models.CharField(max_length=10, default='INR')

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default='razorpay')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created')

    # Optional plan mapping (e.g., for subscriptions)
    plan = models.CharField(max_length=50, blank=True, null=True)

    notes = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['purchase_token']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['provider', 'status']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        id_part = self.order_id or (self.purchase_token[:10] + '...') if self.purchase_token else 'n/a'
        return f"{self.user} - {self.provider}:{id_part} - {self.status}"