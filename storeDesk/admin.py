from decimal import Decimal
from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.html import format_html
from django.utils import timezone
from .models import Genre, Comic, Order, Review, Wishlist, Promotion, PromotionRedemption



class GenreAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)
    list_filter = ('created_at',)
    readonly_fields = ('id', 'created_at')


class ComicAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'price', 'discount_price', 'stock_quantity', 'rating', 'buyer_count', 'created_at')
    search_fields = ('title', 'genres__name')
    list_filter = ('created_at', 'genres', 'stock_quantity')
    readonly_fields = ('id', 'rating', 'rating_count', 'buyer_count', 'created_at')
    fields = ('title', 'cover_image', 'price', 'discount_price', 'description', 'pages', 'genres',
              'stock_quantity', 'preview_file', 'rating', 'rating_count', 'buyer_count', 'created_at')

    def get_fields(self, request, obj=None):
        return super().get_fields(request, obj)

    def low_stock_alert(self, obj):
        return obj.stock_quantity < 10
    low_stock_alert.boolean = True
    low_stock_alert.short_description = 'Low Stock (<10)'


class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'comic', 'purchase_date', 'promo_code', 'discount_applied', 'final_price')
    search_fields = ('user__username', 'comic__title', 'promo_code')
    list_filter = ('purchase_date', 'user')
    readonly_fields = ('id', 'user', 'comic', 'purchase_date', 'buyer_name', 'email', 'mobile', 'address',
                       'pin_code', 'promo_code', 'discount_applied', 'final_price')


class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'comic', 'rating', 'created_at')
    search_fields = ('user__username', 'comic__title', 'comment')
    list_filter = ('created_at', 'user', 'rating')
    readonly_fields = ('id', 'user', 'comic', 'rating', 'comment', 'created_at')


class WishlistAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'comic', 'added_at')
    search_fields = ('user__username', 'comic__title')
    list_filter = ('added_at', 'user')
    readonly_fields = ('id', 'user', 'comic', 'added_at')


class PromotionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'code', 'discount_type', 'discount_value', 'genre', 'comic',
                    'max_uses', 'per_user_limit', 'used_count', 'start_date', 'end_date', 'is_active')
    search_fields = ('title', 'code', 'genre__name', 'comic__title')
    list_filter = ('discount_type', 'start_date', 'end_date', 'genre')
    readonly_fields = ('id', 'used_count')
    fields = ('title', 'code', 'discount_type', 'discount_value', 'terms',
              'genre', 'comic', 'max_uses', 'per_user_limit', 'min_order_amount',
              'start_date', 'end_date')

    def is_active(self, obj):
        return timezone.now() >= obj.start_date and timezone.now() <= obj.end_date
    is_active.boolean = True
    is_active.short_description = 'Active'




admin.site.register(Genre, GenreAdmin)
admin.site.register(Comic, ComicAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(Promotion, PromotionAdmin)
admin.site.register(PromotionRedemption)