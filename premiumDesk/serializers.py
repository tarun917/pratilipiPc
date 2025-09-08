from datetime import timedelta

from django.utils import timezone
from rest_framework import serializers

from .models import SubscriptionModel, WalletLedger


# Server-authoritative subscription catalog
PLAN_PRICING = {
    '3_month': {'months': 3,  'price': 349.00, 'benefits': 'Full access, no ads'},
    '6_month': {'months': 6,  'price': 499.00, 'benefits': 'Full access, no ads'},
    '12_month': {'months': 12, 'price': 799.00, 'benefits': 'Full access, no ads'},  # adjust price if needed
}


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionModel
        fields = ['id', 'user', 'plan', 'price', 'benefits', 'start_date', 'end_date']
        read_only_fields = ['id', 'user', 'price', 'benefits', 'start_date', 'end_date']

    def validate_plan(self, value):
        if value not in PLAN_PRICING:
            raise serializers.ValidationError('Invalid plan')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        plan = validated_data['plan']
        conf = PLAN_PRICING[plan]

        # Enforce one active subscription at a time
        now = timezone.now()
        if SubscriptionModel.objects.filter(user=user, end_date__gt=now).exists():
            raise serializers.ValidationError('You already have an active subscription')

        start = now
        # naive month-add: 30 days per month
        end = start + timedelta(days=30 * conf['months'])

        return SubscriptionModel.objects.create(
            user=user,
            plan=plan,
            price=conf['price'],
            benefits=conf['benefits'],
            start_date=start,
            end_date=end,
        )


class WalletLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletLedger
        fields = [
            'id', 'user', 'delta', 'balance_after', 'reason',
            'link_model', 'link_id', 'idempotency_key', 'created_at'
        ]
        read_only_fields = ['id', 'user', 'delta', 'balance_after', 'created_at']

    # Note: writes to WalletLedger are performed by views/services to ensure
    # atomic updates together with CustomUser.coin_count. This serializer is read-only.


class CoinsConsumeSerializer(serializers.Serializer):
    amount = serializers.IntegerField(min_value=1)
    reason = serializers.ChoiceField(choices=[c[0] for c in WalletLedger.REASON_CHOICES], default='other')
    idempotency_key = serializers.CharField(max_length=64)
    link_model = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)
    link_id = serializers.CharField(max_length=64, required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        # Additional guardrails can be added here if needed (e.g., disallow certain reasons)
        return attrs