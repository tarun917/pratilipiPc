from django.contrib import admin
from .models import SubscriptionModel


@admin.register(SubscriptionModel)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'plan', 'price', 'start_date', 'end_date')
    search_fields = ('user__username', 'user__email', 'plan')
    list_filter = ('plan', 'start_date', 'end_date')
    date_hierarchy = 'start_date'
    ordering = ('-start_date',)
    readonly_fields = ('start_date',)