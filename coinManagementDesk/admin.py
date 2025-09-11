from django.contrib import admin
from .models import CoinModel


@admin.register(CoinModel)
class CoinAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance', 'updated_at')
    readonly_fields = ('user', 'balance', 'updated_at')

    def has_add_permission(self, request):
        return False  # prevent manual creation

    def has_change_permission(self, request, obj=None):
        # allow viewing detail page, but fields are read-only
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False  # prevent deletion

    def save_model(self, request, obj, form, change):
        # hard stop on save attempts (defense-in-depth)
        return