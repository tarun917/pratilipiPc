from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser  # Assuming your custom user model is named CustomUser

class CustomUserAdmin(UserAdmin):
    # Remove 'date_joined' from fields/fieldsets if present
    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'mobile_number', 'profile_image', 'badge')}),  # Removed 'bio'
        # Do NOT include 'date_joined' here
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),  # Only 'last_login', not 'date_joined'
    )
    list_display = (
        'username', 'email', 'mobile_number', 'full_name', 'unique_id',
        'profile_image', 'about', 'coin_count', 'is_active', 'is_staff'
    )
    # ...other config...

admin.site.register(CustomUser, CustomUserAdmin)