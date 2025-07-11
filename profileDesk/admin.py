from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

@admin.register(CustomUser)
class AppUserAdmin(UserAdmin):
    model = CustomUser
    verbose_name = "App User"
    verbose_name_plural = "App Users"

    # Fields to display in the list view
    list_display = (
        'username', 'email', 'mobile_number', 'full_name', 'unique_id',
        'profile_image', 'about', 'coin_count', 'is_active', 'is_staff'
    )

    # Search by email or mobile number
    search_fields = ('email', 'mobile_number')
    search_help_text = "Search by Email ID or Mobile Number"

    # Fields in the detail view
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal Info', {
            'fields': (
                'full_name', 'email', 'mobile_number', 'unique_id',
                'profile_image', 'about', 'coin_count'
            )
        }),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Read-only fields
    readonly_fields = ('unique_id', 'date_joined', 'last_login')

    # Filters for navigation
    list_filter = ('is_active', 'is_staff')

    def get_queryset(self, request):
        return super().get_queryset(request).select_related()