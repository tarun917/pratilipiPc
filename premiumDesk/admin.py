from django.contrib import admin
from .models import SubscriptionModel

@admin.register(SubscriptionModel)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'price', 'start_date', 'end_date')