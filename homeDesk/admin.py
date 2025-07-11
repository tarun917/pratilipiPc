from django.contrib import admin
from .models import HomeTabConfig

@admin.register(HomeTabConfig)
class HomeTabConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'updated_at')
    search_fields = ('key', 'value')