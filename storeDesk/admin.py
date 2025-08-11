from django.contrib import admin
from django.db.models import Count, Sum  # Aggregates for analytics
from django.urls import reverse
from django.utils.html import format_html
from django.utils import timezone  # For time zone-aware datetime
from .models import Genre, Comic, Order, Review, Wishlist, Promotion, NotificationPreference, RestockNotification

# Custom Admin Classes
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
    fields = ('title', 'cover_image', 'price', 'discount_price', 'description', 'pages', 'genres', 'stock_quantity', 'preview_file', 'rating', 'rating_count', 'buyer_count', 'created_at')

    def get_readonly_fields(self, request, obj=None):
        if obj:  # Editing an existing object
            return self.readonly_fields + ('title', 'cover_image', 'price', 'discount_price', 'description', 'pages', 'genres', 'stock_quantity', 'preview_file')
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not change:  # Only for new objects
            obj.save()

    def preview_image(self, obj):
        if obj.cover_image:
            return format_html('<img src="{}" width="100" height="100" />', obj.cover_image.url)
        return "No image"
    preview_image.short_description = 'Cover Preview'

    def preview_file_link(self, obj):
        if obj.preview_file:
            return format_html('<a href="{}" target="_blank">View Preview</a>', obj.preview_file.url)
        return "No preview"
    preview_file_link.short_description = 'Preview File'

    def get_fields(self, request, obj=None):
        # Only include model fields, not custom methods
        return super().get_fields(request, obj)

    def low_stock_alert(self, obj):
        return obj.stock_quantity < 10
    low_stock_alert.boolean = True
    low_stock_alert.short_description = 'Low Stock (<10)'

class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'comic', 'purchase_date')
    search_fields = ('user__username', 'comic__title')
    list_filter = ('purchase_date', 'user')
    readonly_fields = ('id', 'user', 'comic', 'purchase_date', 'buyer_name', 'email', 'mobile', 'address', 'pin_code')

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
    list_display = ('id', 'title', 'genre', 'discount_percentage', 'start_date', 'end_date', 'is_active')
    search_fields = ('title', 'genre__name')
    list_filter = ('start_date', 'end_date', 'genre')
    readonly_fields = ('id',)
    fields = ('title', 'genre', 'discount_percentage', 'start_date', 'end_date')

    def is_active(self, obj):
        return timezone.now() >= obj.start_date and timezone.now() <= obj.end_date
    is_active.boolean = True
    is_active.short_description = 'Active'

class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'promotion_notifications')
    search_fields = ('user__username',)
    list_filter = ('promotion_notifications',)
    readonly_fields = ('id', 'user', 'promotion_notifications')

class RestockNotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'comic', 'requested_at', 'notified')
    search_fields = ('user__username', 'comic__title')
    list_filter = ('notified', 'requested_at')
    readonly_fields = ('id', 'user', 'comic', 'requested_at', 'notified')

    def has_add_permission(self, request):
        return False  # Prevent adding new restock notifications via admin

    def notify_users(self, request, queryset):
        for notification in queryset:
            if notification.comic.stock_quantity > 0 and not notification.notified:
                # Placeholder for notification trigger (e.g., Firebase)
                print(f"Triggering notification for {notification.user.username} - {notification.comic.title} restocked")
                notification.notified = True
                notification.save()
    notify_users.short_description = "Notify Selected Users"

    actions = ['notify_users']

# Analytics Dashboard (Temporary Comment due to django-admin-charts issue)
# class StoreAnalyticsAdmin(admin.ModelAdmin):
#     change_list_template = 'admin/analytics_change_list.html'
#
#     def changelist_view(self, request, extra_context=None):
#         # Top-selling comics
#         top_comics = Comic.objects.annotate(buyer_count=Count('order')).order_by('-buyer_count')[:5]
#         top_comics_data = [{"label": c.title, "value": c.buyer_count} for c in top_comics]
#
#         # Genre popularity
#         genre_popularity = Genre.objects.annotate(comic_count=Count('comic')).order_by('-comic_count')
#         genre_data = [{"label": g.name, "value": g.comic_count} for g in genre_popularity]
#
#         # Revenue (simplified)
#         total_revenue = Order.objects.aggregate(total=Sum('comic__price'))['total'] or 0
#
#         extra_context = extra_context or {}
#         extra_context['top_comics_chart'] = {'type': 'bar', 'data': top_comics_data, 'title': 'Top 5 Selling Comics'}
#         extra_context['genre_chart'] = {'type': 'pie', 'data': genre_data, 'title': 'Genre Popularity'}
#         extra_context['revenue'] = total_revenue
#         return super().changelist_view(request, extra_context)
#
# # Registration (Temporary Comment)
# # admin.site.register(Comic, StoreAnalyticsAdmin)  # Reuse Comic for analytics

# Register Models with Admin
admin.site.register(Genre, GenreAdmin)
admin.site.register(Comic, ComicAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Wishlist, WishlistAdmin)
admin.site.register(Promotion, PromotionAdmin)
admin.site.register(NotificationPreference, NotificationPreferenceAdmin)
admin.site.register(RestockNotification, RestockNotificationAdmin)
# admin.site.register(Comic, StoreAnalyticsAdmin)  # Temporary comment