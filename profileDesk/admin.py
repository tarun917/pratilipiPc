from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Address


class AddressInline(admin.TabularInline):
    model = Address
    fields = (
        'name', 'mobile_number', 'line1', 'city', 'state', 'pincode',
        'country', 'address_type', 'is_default',
    )
    extra = 0
    show_change_link = True


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {
            'fields': (
                'full_name', 'email', 'mobile_number',
                'profile_image', 'about', 'badge', 'coin_count',
            )
        }),
        ('Identifiers', {'fields': ('unique_id',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'full_name', 'email', 'mobile_number', 'password1', 'password2'),
        }),
    )

    list_display = (
        'username', 'email', 'mobile_number', 'full_name', 'badge',
        'coin_count', 'is_active', 'is_staff', 'is_superuser',
    )
    list_filter = ('is_active', 'is_staff', 'is_superuser', 'badge')
    search_fields = ('username', 'email', 'mobile_number', 'full_name', 'unique_id')
    ordering = ('username',)

    # Make both unique_id and coin_count read-only in admin
    readonly_fields = ('unique_id', 'coin_count')

    inlines = [AddressInline]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'name', 'city', 'state', 'pincode',
        'country', 'address_type', 'is_default', 'updated_at',
    )
    list_filter = ('address_type', 'is_default', 'city', 'state', 'country')
    search_fields = (
        'user__username', 'user__email', 'name', 'mobile_number',
        'line1', 'line2', 'landmark', 'city', 'pincode',
    )
    ordering = ('-is_default', '-updated_at')
    list_select_related = ('user',)