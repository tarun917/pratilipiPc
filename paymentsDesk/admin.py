from django.contrib import admin
from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'order_id', 'payment_id', 'amount', 'currency', 'status', 'plan', 'created_at')
    search_fields = ('user__username', 'user__email', 'order_id', 'payment_id', 'plan')
    list_filter = ('status', 'currency', 'plan', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)