from django.contrib import admin
from .models import CoinModel

@admin.register(CoinModel)
class CoinAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')