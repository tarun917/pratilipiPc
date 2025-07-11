from django.contrib import admin
from .models import FavouriteModel

@admin.register(FavouriteModel)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'comic_type', 'comic_id', 'created_at')  # Columns to display
    list_filter = ('comic_type', 'created_at')  # Filters for easy navigation
    search_fields = ('user__username', 'comic_id')  # Search by username or comic_id
    date_hierarchy = 'created_at'  # Date-based navigation

    # Optional: Add custom actions (e.g., bulk delete)
    actions = ['make_sample_action']

    def make_sample_action(self, request, queryset):
        queryset.update(comic_type='digital')  # Example action
        self.message_user(request, "Selected favourites updated to 'digital' type.")
    make_sample_action.short_description = "Mark selected as Digital"