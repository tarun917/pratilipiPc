from decimal import Decimal
from django.db import models
from django.utils import timezone
from profileDesk.models import CustomUser


class Genre(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Comic(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    cover_image = models.ImageField(upload_to='comics/covers/', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    description = models.TextField()
    pages = models.PositiveIntegerField()
    rating = models.DecimalField(max_digits=3, decimal_places=1, default=Decimal('0.0'))
    rating_count = models.PositiveIntegerField(default=0)
    buyer_count = models.PositiveIntegerField(default=0)
    stock_quantity = models.PositiveIntegerField(default=0)
    preview_file = models.FileField(upload_to='comics/previews/', null=True, blank=True)
    genres = models.ManyToManyField(Genre)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    purchase_date = models.DateTimeField(auto_now_add=True)
    buyer_name = models.CharField(max_length=255)
    email = models.EmailField()
    mobile = models.CharField(max_length=15)
    address = models.TextField()
    pin_code = models.CharField(max_length=10)

    # Promo fields
    promo_code = models.CharField(max_length=32, null=True, blank=True)
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    final_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"


class Review(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} on {self.comic.title}"


class Wishlist(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    comic = models.ForeignKey(Comic, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comic')

    def __str__(self):
        return f"{self.user.username}'s wishlist item {self.comic.title}"


class Promotion(models.Model):
    DISCOUNT_TYPE_CHOICES = (
        ('percentage', 'percentage'),
        ('fixed', 'fixed'),
    )

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)

    # Applicability: genre or specific comic (either/both null => apply to all)
    genre = models.ForeignKey(Genre, on_delete=models.SET_NULL, null=True, blank=True)
    comic = models.ForeignKey(Comic, on_delete=models.SET_NULL, null=True, blank=True)

    # Promo code fields
    # Make code nullable for existing rows; can enforce non-null later after backfill
    code = models.CharField(max_length=32, unique=True, null=True, blank=True)
    discount_type = models.CharField(max_length=16, choices=DISCOUNT_TYPE_CHOICES, default='percentage')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    terms = models.TextField(null=True, blank=True)

    # Limits and window
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    per_user_limit = models.PositiveIntegerField(null=True, blank=True)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

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

    def __str__(self):
        return f"{self.user.username} -> {self.promotion.code} (Order {self.order.id})"