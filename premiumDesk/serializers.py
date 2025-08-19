# premiumDesk/serializers.py
from rest_framework import serializers
from .models import SubscriptionModel
from django.utils import timezone
from datetime import timedelta

PLAN_PRICING = {
    '3_month': {'months': 3,  'price': 349.00, 'benefits': 'Full access, no ads'},
    '6_month': {'months': 6,  'price': 499.00, 'benefits': 'Full access, no ads'},
    '12_month': {'months': 12, 'price': 799.00, 'benefits': 'Full access, no ads'},  # adjust price
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
        # naive month-add: use 30 days per month or use dateutil.relativedelta if available
        end = start + timedelta(days=30 * conf['months'])

        return SubscriptionModel.objects.create(
            user=user,
            plan=plan,
            price=conf['price'],
            benefits=conf['benefits'],
            start_date=start,
            end_date=end,
        )