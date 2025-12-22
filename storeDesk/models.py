from decimal import Decimal
from django.db import models
from django.forms import ValidationError
from django.utils import timezone
from profileDesk.models import CustomUser, Address
from django.core.validators import MinValueValidator, MaxValueValidator


class Genre(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.name


class Comic(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    cover_image = models.ImageField(upload_to="comics/covers/", null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    pages = models.PositiveIntegerField()
    rating = models.DecimalField(
    max_digits=3,
    decimal_places=1,
    default=Decimal("0.0"),
    validators=[MinValueValidator(Decimal("0.0")), MaxValueValidator(Decimal("5.0"))],
    help_text="Average rating between 0.0 and 5.0")
    rating_count = models.PositiveIntegerField(default=0, help_text="Number of ratings contributing to average")
    buyer_count = models.PositiveIntegerField(default=0)
    stock_quantity = models.PositiveIntegerField(default=0)
    preview_file = models.FileField(upload_to="comics/previews/", null=True, blank=True)
    genres = models.ManyToManyField(Genre)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["title"]),
            models.Index(fields=["-rating"]),
            models.Index(fields=["stock_quantity"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.title
    
    def validate_rating(self, value):
        if value < Decimal("0.0") or value > Decimal("5.0"):
            raise ValidationError("Rating must be between 0.0 and 5.0.")
        return value


class Order(models.Model):
    PAYMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
        ("cancelled", "Cancelled"),
    )

    FULFILLMENT_STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("shipped", "Shipped"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    )

    GATEWAY_CHOICES = (
        ("razorpay", "Razorpay"),
        ("none", "None"),
    )

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name="store_orders")

    # Legacy single-item fields (optional in multi-item mode)
    comic = models.ForeignKey("Comic", on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Quantity for legacy single-item orders. Leave null when using OrderItem rows.",
    )

    # Order timestamps (keep your purchase_date; also track updates)
    purchase_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    # Address linkage + immutable snapshot for fulfillment
    address = models.ForeignKey(Address, on_delete=models.PROTECT, null=True, blank=True, related_name="orders")
    ship_name = models.CharField(max_length=100)
    ship_mobile = models.CharField(max_length=15)
    ship_line1 = models.CharField(max_length=255)
    ship_line2 = models.CharField(max_length=255, null=True, blank=True)
    ship_landmark = models.CharField(max_length=255, null=True, blank=True)
    ship_city = models.CharField(max_length=100)
    ship_state = models.CharField(max_length=100)
    ship_pincode = models.CharField(max_length=20)
    ship_country = models.CharField(max_length=64, default="India")

    # Promo/totals (server computed)
    promo_code = models.CharField(max_length=32, null=True, blank=True)
    discount_applied = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Total discount applied at order level (may include line discounts sum)."
    )
    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Sum before order-level discounts; for legacy single-item this is unit*qty."
    )
    shipping_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Shipping charges applied to the order."
    )
    tax_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Tax (e.g., GST) applied to the order."
    )
    final_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Grand total after discounts, shipping, and taxes."
    )

    # Gateway coupling (paymentsDesk will populate and manage these)
    gateway = models.CharField(max_length=16, choices=GATEWAY_CHOICES, default="none", db_index=True)
    gateway_order_id = models.CharField(
        max_length=128, null=True, blank=True,
        help_text="Gateway Order ID (e.g., Razorpay order_id).", unique=True
    )
    gateway_payment_id = models.CharField(
        max_length=128, null=True, blank=True,
        help_text="Gateway Payment ID (e.g., Razorpay payment_id)."
    )
    gateway_signature = models.CharField(
        max_length=256, null=True, blank=True,
        help_text="Gateway signature (e.g., Razorpay signature)."
    )
    amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Amount expected to be paid via gateway for this order (should equal final_price)."
    )

    payment_status = models.CharField(
        max_length=16, choices=PAYMENT_STATUS_CHOICES, default="pending", db_index=True
    )
    fulfillment_status = models.CharField(
        max_length=16, choices=FULFILLMENT_STATUS_CHOICES, default="pending", db_index=True
    )

    # Idempotency for create/confirm flows
    idempotency_key = models.CharField(
        max_length=64, null=True, blank=True, unique=True,
        help_text="Client-supplied unique key to prevent duplicate order creations."
    )

    class Meta:
        ordering = ("-purchase_date",)
        indexes = [
            models.Index(fields=["user", "-purchase_date"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["fulfillment_status"]),
            models.Index(fields=["promo_code"]),
            models.Index(fields=["gateway"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=(models.Q(quantity__isnull=True) | models.Q(quantity__gte=1)),
                name="order_quantity_null_or_gte_1",
            ),
            models.CheckConstraint(check=models.Q(discount_applied__gte=0), name="order_discount_gte_0"),
            models.CheckConstraint(check=models.Q(final_price__gte=0), name="order_final_price_gte_0"),
            models.CheckConstraint(check=models.Q(amount__gte=0), name="order_amount_gte_0"),
            models.CheckConstraint(check=models.Q(subtotal__gte=0), name="order_subtotal_gte_0"),
            models.CheckConstraint(check=models.Q(shipping_fee__gte=0), name="order_shipping_fee_gte_0"),
            models.CheckConstraint(check=models.Q(tax_amount__gte=0), name="order_tax_amount_gte_0"),
        ]

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

    @property
    def is_paid(self):
        return self.payment_status == "paid"


class OrderItem(models.Model):
    """
    Line item for multi-item orders.
    For legacy single-item orders, you may leave Order.comic/quantity populated and not create OrderItem rows.
    For multi-item orders, leave Order.comic/quantity null and create one or more OrderItem entries.
    """
    id = models.AutoField(primary_key=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    comic = models.ForeignKey(Comic, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Unit price considered for this item before per-item discount."
    )
    discount_applied = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"),
        help_text="Discount applied to this line."
    )
    final_price = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Line total after discount = (unit_price * quantity) - discount_applied",
    )

    class Meta:
        indexes = [
            models.Index(fields=["order"]),
            models.Index(fields=["comic"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(quantity__gte=1), name="orderitem_quantity_gte_1"),
            models.CheckConstraint(check=models.Q(unit_price__gte=0), name="orderitem_unit_price_gte_0"),
            models.CheckConstraint(check=models.Q(discount_applied__gte=0), name="orderitem_discount_gte_0"),
            models.CheckConstraint(check=models.Q(final_price__gte=0), name="orderitem_final_price_gte_0"),
        ]

    def __str__(self):
        return f"OrderItem {self.id} - Order {self.order_id} - Comic {self.comic_id}"


class Review(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["comic", "-created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"Review by {self.user.username} on {self.comic.title}"


class Wishlist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "comic")
        ordering = ("-added_at",)
        indexes = [
            models.Index(fields=["user", "-added_at"]),
            models.Index(fields=["comic"]),
        ]

    def __str__(self):
        return f"{self.user.username}'s wishlist item {self.comic.title}"


class Promotion(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ("percentage", "percentage"),
        ("fixed", "fixed"),
    )

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)

    # Applicability: genre or specific comic (either/both null => apply to all)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True)
    comic = models.ForeignKey(Comic, on_delete=models.SET_NULL, null=True, blank=True)

    # Promo code fields
    code = models.CharField(max_length=32, unique=True, null=True, blank=True)
    discount_type = models.CharField(max_length=16, choices=DISCOUNT_TYPE_CHOICES, default="percentage")
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    terms = models.TextField(null=True, blank=True)

    # Limits and window
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

    class Meta:
        ordering = ("-end_date",)
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["genre"]),
            models.Index(fields=["comic"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.code or 'NO-CODE'})"

    @property
    def is_active(self):
        now = timezone.now()
        return self.start_date <= now <= self.end_date


class PromotionRedemption(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    promotion = models.ForeignKey(Promotion, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-redeemed_at",)
        indexes = [
            models.Index(fields=["user", "-redeemed_at"]),
            models.Index(fields=["promotion"]),
            models.Index(fields=["order"]),
        ]

    def __str__(self):
        return f"{self.user.username} -> {self.promotion.code} (Order {self.order.id})"