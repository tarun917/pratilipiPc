from decimal import Decimal
import re

from django.core.exceptions import ValidationError
from rest_framework import serializers

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
from profileDesk.models import CustomUser, Address


# -------------------------
# Genre
# -------------------------
class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ["id", "name", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_name(self, value):
        if not value.strip():
            raise ValidationError("Genre name cannot be empty.")
        if len(value) > 100:
            raise ValidationError("Genre name must not exceed 100 characters.")
        return value


# -------------------------
# Comic
# -------------------------
class ComicSerializer(serializers.ModelSerializer):
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Comic
        fields = [
            "id",
            "title",
            "cover_image",
            "price",
            "discount_price",
            "description",
            "pages",
            "rating",
            "rating_count",
            "buyer_count",
            "stock_quantity",
            "preview_file",
            "genres",
            "created_at",
        ]
        read_only_fields = ["id", "rating", "rating_count", "buyer_count", "created_at"]

    def validate_title(self, value):
        if not value.strip():
            raise ValidationError("Title cannot be empty.")
        if len(value) > 200:
            raise ValidationError("Title must not exceed 200 characters.")
        return value

    def validate_price(self, value):
        if value <= 0:
            raise ValidationError("Price must be greater than zero.")
        return value

    def validate_discount_price(self, value):
        price_raw = self.initial_data.get("price")
        price = Decimal(str(price_raw)) if price_raw is not None else None
        if value and price and value >= price:
            raise ValidationError("Discount price must be less than regular price.")
        return value

    def validate_description(self, value):
        if not value.strip():
            raise ValidationError("Description cannot be empty.")
        words = value.split()
        if len(words) > 500:
            raise ValidationError("Description must not exceed 500 words.")
        return value

    def validate_pages(self, value):
        if value <= 0:
            raise ValidationError("Pages must be greater than zero.")
        return value

    def validate_stock_quantity(self, value):
        if value < 0:
            raise ValidationError("Stock quantity cannot be negative.")
        return value

    def validate_cover_image(self, value):
        if value and value.size > 5 * 1024 * 1024:
            raise ValidationError("Cover image size must not exceed 5MB.")
        if value and not value.name.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
            raise ValidationError("Only JPG, JPEG, PNG, and GIF formats are allowed.")
        return value

    def validate_preview_file(self, value):
        if value and value.size > 10 * 1024 * 1024:
            raise ValidationError("Preview file size must not exceed 10MB.")
        if value and not value.name.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".pdf")):
            raise ValidationError("Only JPG, JPEG, PNG, GIF, and PDF formats are allowed.")
        return value


# -------------------------
# Order / OrderItem
# -------------------------
def compute_unit_price(comic: Comic) -> Decimal:
    """
    If comic.discount_price is set, use it; else use comic.price.
    """
    if comic.discount_price is not None:
        return Decimal(comic.discount_price)
    return Decimal(comic.price)


class OrderItemInputSerializer(serializers.Serializer):
    comic = serializers.PrimaryKeyRelatedField(queryset=Comic.objects.all())
    quantity = serializers.IntegerField(min_value=1, required=True)


class OrderItemSerializer(serializers.ModelSerializer):
    comic = serializers.PrimaryKeyRelatedField(queryset=Comic.objects.all())

    class Meta:
        model = OrderItem
        fields = ["id", "comic", "quantity", "unit_price", "discount_applied", "final_price"]
        read_only_fields = ["id", "unit_price", "discount_applied", "final_price"]


class OrderSerializer(serializers.ModelSerializer):
    """
    Create shapes:
    1) Legacy single-item:
       {
         address_id: int,
         comic: int,
         quantity: int (>=1),
         promo_code?, idempotency_key?
       }
    2) Multi-item:
       {
         address_id: int,
         items: [{ comic: int, quantity: int }, ...],
         promo_code?, idempotency_key?
       }
    """
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), required=False, default=serializers.CurrentUserDefault()
    )
    address_id = serializers.PrimaryKeyRelatedField(
        queryset=Address.objects.all(), write_only=True, required=True, source="address"
    )
    promo_code = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)
    idempotency_key = serializers.CharField(write_only=True, required=False, allow_blank=True, allow_null=True)

    # legacy fields
    comic = serializers.PrimaryKeyRelatedField(queryset=Comic.objects.all(), required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, required=False, allow_null=True)

    # multi-item fields
    items = OrderItemInputSerializer(many=True, required=False)

    # nested read-only items on response
    line_items = OrderItemSerializer(source="items", many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "user",
            "purchase_date",
            "address_id",
            "promo_code",
            "idempotency_key",
            # legacy single-item
            "comic",
            "quantity",
            # multi-item
            "items",
            "line_items",
            # totals
            "subtotal",
            "discount_applied",
            "shipping_fee",
            "tax_amount",
            "final_price",
            # payment (read-only)
            "payment_status",
            "fulfillment_status",
            "gateway",
            "gateway_order_id",
            "gateway_payment_id",
            "gateway_signature",
            "amount",
        ]
        read_only_fields = [
            "id",
            "purchase_date",
            "subtotal",
            "discount_applied",
            "shipping_fee",
            "tax_amount",
            "final_price",
            "payment_status",
            "fulfillment_status",
            "gateway",
            "gateway_order_id",
            "gateway_payment_id",
            "gateway_signature",
            "amount",
            "line_items",
        ]

    # ---------- shape + stock validation ----------
    def validate(self, attrs):
        items = attrs.get("items")
        comic = attrs.get("comic")
        quantity = attrs.get("quantity")

        if items and (comic or quantity):
            raise ValidationError("Provide either items[] for multi-item or comic+quantity for single-item, not both.")

        if items:
            if not isinstance(items, list) or len(items) == 0:
                raise ValidationError("items must be a non-empty list.")
            for idx, it in enumerate(items):
                c: Comic = it["comic"]
                q: int = it["quantity"]
                if c.stock_quantity < q:
                    raise ValidationError(f"Item {idx + 1}: '{c.title}' has only {c.stock_quantity} in stock.")
        else:
            if not comic:
                raise ValidationError("comic is required when items are not provided.")
            q = quantity or 1
            if comic.stock_quantity < q:
                raise ValidationError(f"'{comic.title}' has only {comic.stock_quantity} in stock.")
            attrs["quantity"] = q

        return attrs

    # ---------- create ----------
    def create(self, validated_data):
        """
        Create Order and (if provided) OrderItems.
        - Snapshots address into ship_* fields.
        - Pricing: Comic.price/discount_price simple logic.
        - Advanced promo_code logic can run in views/services and update totals.
        """
        items_data = validated_data.pop("items", None)
        promo_code = validated_data.pop("promo_code", None)
        idempotency_key = validated_data.pop("idempotency_key", None)
        address_obj: Address = validated_data.pop("address")  # from address_id via source="address"

        # attach request user if missing
        if not validated_data.get("user") and self.context.get("request"):
            validated_data["user"] = self.context["request"].user

        # snapshot address into order fields
        snapshot = dict(
            address=address_obj,
            ship_name=address_obj.name,
            ship_mobile=address_obj.mobile_number,   # changed from mobile
            ship_line1=address_obj.line1,            # changed from address_line1
            ship_line2=address_obj.line2,            # changed from address_line2
            ship_landmark=address_obj.landmark,
            ship_city=address_obj.city,
            ship_state=address_obj.state,
            ship_pincode=address_obj.pincode,
            ship_country=getattr(address_obj, "country", "India"),
        )

        subtotal = Decimal("0.00")
        discount_total = Decimal("0.00")

        if items_data:
            # multi-item mode
            validated_data["comic"] = None
            validated_data["quantity"] = None
            order: Order = Order.objects.create(
                promo_code=promo_code or None,
                idempotency_key=idempotency_key or None,
                **snapshot,
                **validated_data,
            )

            line_objs = []
            for it in items_data:
                comic = it["comic"]
                qty = int(it["quantity"])
                unit_price = compute_unit_price(comic)
                line_subtotal = unit_price * qty
                line_discount = Decimal("0.00")
                line_final = line_subtotal - line_discount

                subtotal += line_subtotal
                discount_total += line_discount

                line_objs.append(
                    OrderItem(
                        order=order,
                        comic=comic,
                        quantity=qty,
                        unit_price=unit_price,
                        discount_applied=line_discount,
                        final_price=line_final,
                    )
                )

            OrderItem.objects.bulk_create(line_objs)

            order.subtotal = subtotal
            order.discount_applied = discount_total
            order.final_price = subtotal - discount_total
            order.amount = order.final_price
            order.save(update_fields=["subtotal", "discount_applied", "final_price", "amount"])
            return order

        else:
            # legacy single-item
            comic = validated_data.get("comic")
            qty = int(validated_data.get("quantity") or 1)

            unit_price = compute_unit_price(comic)
            line_subtotal = unit_price * qty
            line_discount = Decimal("0.00")
            line_final = line_subtotal - line_discount

            subtotal = line_subtotal
            discount_total = line_discount
            final_price = line_final

            order: Order = Order.objects.create(
                promo_code=promo_code or None,
                idempotency_key=idempotency_key or None,
                subtotal=subtotal,
                discount_applied=discount_total,
                final_price=final_price,
                amount=final_price,
                **snapshot,
                **validated_data,
            )
            return order


# -------------------------
# Quote Serializers (for /api/store/orders/quote)
# -------------------------
class QuoteItemSerializer(serializers.Serializer):
    comic = serializers.PrimaryKeyRelatedField(queryset=Comic.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class QuoteRequestSerializer(serializers.Serializer):
    # Either provide comic+quantity or items[]
    comic = serializers.PrimaryKeyRelatedField(queryset=Comic.objects.all(), required=False)
    quantity = serializers.IntegerField(min_value=1, required=False)
    items = QuoteItemSerializer(many=True, required=False)
    promo_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        items = attrs.get("items")
        comic = attrs.get("comic")
        qty = attrs.get("quantity")

        if items and (comic or qty):
            raise ValidationError("Provide either items[] or comic+quantity, not both.")
        if items:
            if len(items) == 0:
                raise ValidationError("items must be a non-empty list.")
            for idx, it in enumerate(items):
                c: Comic = it["comic"]
                q: int = it["quantity"]
                if c.stock_quantity < q:
                    raise ValidationError(f"Item {idx + 1}: '{c.title}' has only {c.stock_quantity} in stock.")
        else:
            if not comic:
                raise ValidationError("comic is required when items are not provided.")
            q = qty or 1
            if comic.stock_quantity < q:
                raise ValidationError(f"'{comic.title}' has only {comic.stock_quantity} in stock.")
            attrs["quantity"] = q

        return attrs


class QuoteLineResponseSerializer(serializers.Serializer):
    comic = serializers.IntegerField()
    quantity = serializers.IntegerField()
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_applied = serializers.DecimalField(max_digits=10, decimal_places=2)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2)


class QuoteResponseSerializer(serializers.Serializer):
    items = QuoteLineResponseSerializer(many=True)
    subtotal = serializers.DecimalField(max_digits=10, decimal_places=2)
    discount_total = serializers.DecimalField(max_digits=10, decimal_places=2)
    final_price = serializers.DecimalField(max_digits=10, decimal_places=2)
    eligible_comics = serializers.ListField(
        child=serializers.IntegerField(), required=False
    )


# -------------------------
# Review
# -------------------------
class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)

    class Meta:
        model = Review
        fields = ["id", "user", "comic", "rating", "comment", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_rating(self, value):
        if value not in range(1, 6):
            raise ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_comment(self, value):
        if not value.strip():
            raise ValidationError("Comment cannot be empty.")
        if len(value) > 1000:
            raise ValidationError("Comment must not exceed 1000 characters.")
        return value

    def validate(self, data):
        user = self.context["request"].user if "request" in self.context else None
        if not user:
            raise ValidationError("Authentication required.")
        purchased_legacy = Order.objects.filter(
            user=user, comic=data["comic"], payment_status="paid"
        ).exists()
        purchased_multi = OrderItem.objects.filter(
            order__user=user, order__payment_status="paid", comic=data["comic"]
        ).exists()
        if not (purchased_legacy or purchased_multi):
            raise ValidationError("You can only review a comic you have purchased.")
        return data


# -------------------------
# Wishlist
# -------------------------
class WishlistSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all(), required=False, default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Wishlist
        fields = ["id", "user", "comic", "added_at"]
        read_only_fields = ["id", "added_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].required = False


# -------------------------
# Promotion
# -------------------------
class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = [
            "id",
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
            "used_count",
            "start_date",
            "end_date",
        ]
        read_only_fields = ["id", "used_count"]

    def validate_code(self, value):
        if value in (None, ""):
            return None
        v = value.strip().upper()
        if not re.match(r"^[A-Z0-9_-]{3,32}$", v):
            raise ValidationError("Code must be 3-32 chars, uppercase letters, digits, _ or -.")
        return v

    def validate(self, data):
        if data["start_date"] >= data["end_date"]:
            raise ValidationError("Start date must be before end date.")
        if data["discount_type"] == "percentage":
            if data["discount_value"] < 0 or data["discount_value"] > 100:
                raise ValidationError("Percentage must be between 0 and 100.")
        else:
            if data["discount_value"] < 0:
                raise ValidationError("Fixed discount must be >= 0.")
        return data


class DevConfirmRequestSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["paid", "failed"])