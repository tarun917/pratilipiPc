from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from profileDesk.models import CustomUser

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
