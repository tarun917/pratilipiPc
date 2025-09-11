from django.contrib import admin
from django.utils import timezone

from .models import (
    Genre,
    Comic,
    Order,
    OrderItem,
    Review,
    Wishlist,
    Promotion,
    PromotionRedemption,
)

# ---------- Genre ----------
@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "created_at")
    search_fields = ("name",)
    list_filter = ("created_at",)
    readonly_fields = ("id", "created_at")


# ---------- Comic ----------
@admin.register(Comic)
class ComicAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "price",
        "discount_price",
        "stock_quantity",
        "low_stock_alert",
        "rating",
        "buyer_count",
        "created_at",
    )
    search_fields = ("title", "genres__name")
    list_filter = ("created_at", "genres", "stock_quantity")
    readonly_fields = ("id", "rating", "rating_count", "buyer_count", "created_at")
    fields = (
        "title",
        "cover_image",
        "price",
        "discount_price",
        "description",
        "pages",
        "genres",
        "stock_quantity",
        "preview_file",
        "rating",
        "rating_count",
        "buyer_count",
        "created_at",
    )

    @admin.display(boolean=True, description="Low Stock (<10)")
    def low_stock_alert(self, obj: Comic) -> bool:
        return obj.stock_quantity < 10


# ---------- Order / OrderItem ----------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ("comic",)
    fields = ("comic", "quantity", "unit_price", "discount_applied", "final_price")
    readonly_fields = ("unit_price", "discount_applied", "final_price")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "purchase_date",
        "mode",
        "items_count",
        "promo_code",
        "payment_status",
        "gateway",
        "final_price",
    )
    search_fields = (
        "id",
        "user__username",
        "promo_code",
        "gateway_order_id",
        "gateway_payment_id",
    )
    list_filter = (
        "purchase_date",
        "user",
        "payment_status",
        "fulfillment_status",
        "gateway",
        "promo_code",
    )
    date_hierarchy = "purchase_date"
    inlines = [OrderItemInline]

    # Keep financials, gateway identifiers, and address snapshot immutable in admin
    readonly_fields = (
        "id",
        "user",
        "purchase_date",
        "updated_at",
        "paid_at",
        # legacy single-item
        "comic",
        "quantity",
        # address link + snapshot (immutable)
        "address",
        "ship_name",
        "ship_mobile",
        "ship_line1",
        "ship_line2",
        "ship_landmark",
        "ship_city",
        "ship_state",
        "ship_pincode",
        "ship_country",
        # promo + totals
        "promo_code",
        "subtotal",
        "discount_applied",
        "shipping_fee",
        "tax_amount",
        "final_price",
        "amount",
        # gateway identifiers/signature (system-managed)
        "gateway",
        "gateway_order_id",
        "gateway_payment_id",
        "gateway_signature",
        # idempotency
        "idempotency_key",
    )

    # Allow only status edits (manual corrections)
    fields = (
        "id",
        "user",
        "purchase_date",
        "updated_at",
        "paid_at",
        # legacy single-item (optional)
        "comic",
        "quantity",
        # address snapshot
        "address",
        "ship_name",
        "ship_mobile",
        "ship_line1",
        "ship_line2",
        "ship_landmark",
        "ship_city",
        "ship_state",
        "ship_pincode",
        "ship_country",
        # promo + totals
        "promo_code",
        "subtotal",
        "discount_applied",
        "shipping_fee",
        "tax_amount",
        "final_price",
        "amount",
        # statuses editable
        "payment_status",
        "fulfillment_status",
        # gateway (read-only identifiers)
        "gateway",
        "gateway_order_id",
        "gateway_payment_id",
        "gateway_signature",
        "idempotency_key",
    )

    @admin.display(description="Mode")
    def mode(self, obj: Order) -> str:
        # Legacy if comic set; else multi-item
        return "Legacy 1 item" if obj.comic_id else "Multi-item"

    @admin.display(description="Items")
    def items_count(self, obj: Order) -> int:
        if obj.comic_id:
            return obj.quantity or 1
        return obj.items.count()


# Optional: register OrderItem for direct browsing (read-only totals)
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "comic", "quantity", "unit_price", "discount_applied", "final_price")
    search_fields = ("order__id", "comic__title")
    list_filter = ("comic",)
    readonly_fields = ("id", "order", "comic", "quantity", "unit_price", "discount_applied", "final_price")


# ---------- Review ----------
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "comic", "rating", "created_at")
    search_fields = ("user__username", "comic__title", "comment")
    list_filter = ("created_at", "user", "rating")
    readonly_fields = ("id", "user", "comic", "rating", "comment", "created_at")


# ---------- Wishlist ----------
@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "comic", "added_at")
    search_fields = ("user__username", "comic__title")
    list_filter = ("added_at", "user")
    readonly_fields = ("id", "user", "comic", "added_at")


# ---------- Promotion ----------
@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "code",
        "discount_type",
        "discount_value",
        "genre",
        "comic",
        "max_uses",
        "per_user_limit",
        "used_count",
        "start_date",
        "end_date",
        "is_active",
    )
    search_fields = ("title", "code", "genre__name", "comic__title")
    list_filter = ("discount_type", "start_date", "end_date", "genre")
    readonly_fields = ("id", "used_count")
    fields = (
        "title",
        "code",
        "discount_type",
        "discount_value",
        "terms",
        "genre",
        "comic",
        "max_uses",
        "per_user_limit",
        "min_order_amount",
        "start_date",
        "end_date",
    )

    @admin.display(boolean=True, description="Active")
    def is_active(self, obj: Promotion) -> bool:
        now = timezone.now()
        return obj.start_date <= now <= obj.end_date


# ---------- Promotion Redemption ----------
@admin.register(PromotionRedemption)
class PromotionRedemptionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "promotion", "order", "redeemed_at")
    search_fields = ("user__username", "promotion__code", "order__id")
    list_filter = ("redeemed_at", "promotion")
    readonly_fields = ("id", "user", "promotion", "order", "redeemed_at")