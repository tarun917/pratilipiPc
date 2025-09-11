from django.db import models
from profileDesk.models import CustomUser


class SubscriptionModel(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    plan = models.CharField(
        max_length=50,
        choices=[('3_month', '3-Month'), ('6_month', '6-Month'), ('12_month', '12-Month')]
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    benefits = models.TextField()
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=['user', 'end_date']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.plan}"


class WalletLedger(models.Model):
    REASON_CHOICES = [
        ('unlock_episode', 'Unlock Episode'),
        ('admin_adjust', 'Admin Adjust'),
        ('play_credit', 'Play Credit'),
        ('refund', 'Refund'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='wallet_ledger')
    # Positive = credit coins; Negative = debit coins
    delta = models.IntegerField()
    # Balance after applying this entry
    balance_after = models.IntegerField()
    # Optional categorization
    reason = models.CharField(max_length=32, choices=REASON_CHOICES, default='other')
    # Optional linking to a domain object (e.g., digitalcomic episode/payment id)
    link_model = models.CharField(max_length=64, blank=True, null=True)
    link_id = models.CharField(max_length=64, blank=True, null=True)
    # Idempotency key to prevent duplicate writes (e.g., purchaseToken or composed key)
    idempotency_key = models.CharField(max_length=64, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['idempotency_key']),
        ]

    def __str__(self):
        sign = '+' if self.delta >= 0 else ''
        return f"{self.user.username}: {sign}{self.delta} -> {self.balance_after} ({self.reason})"