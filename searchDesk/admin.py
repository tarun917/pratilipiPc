from django.contrib import admin
from .models import SearchFilterModel

@admin.register(SearchFilterModel)
class SearchFilterAdmin(admin.ModelAdmin):
    list_display = ('type', 'filter_name')