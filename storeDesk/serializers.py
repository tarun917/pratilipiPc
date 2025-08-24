from decimal import Decimal
from rest_framework import serializers
from django.core.exceptions import ValidationError
import re
from .models import Genre, Comic, Order, Review, Wishlist, Promotion, PromotionRedemption
from profileDesk.models import CustomUser


class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value):
        if not value.strip():
            raise ValidationError("Genre name cannot be empty.")
        if len(value) > 100:
            raise ValidationError("Genre name must not exceed 100 characters.")
        return value


class ComicSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    genres = GenreSerializer(many=True, read_only=True)

    class Meta:
        model = Comic
        fields = ['id', 'title', 'cover_image', 'price', 'discount_price', 'description', 'pages',
                  'rating', 'rating_count', 'buyer_count', 'stock_quantity', 'preview_file',
                  'genres', 'created_at', 'user']
        read_only_fields = ['id', 'rating', 'rating_count', 'buyer_count', 'created_at']

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
        price_raw = self.initial_data.get('price')
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
        if value and not value.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
            raise ValidationError("Only JPG, JPEG, PNG, and GIF formats are allowed.")
        return value

    def validate_preview_file(self, value):
        if value and value.size > 10 * 1024 * 1024:
            raise ValidationError("Preview file size must not exceed 10MB.")
        if value and not value.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.pdf')):
            raise ValidationError("Only JPG, JPEG, PNG, GIF, and PDF formats are allowed.")
        return value


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)
    # Accept promo_code from client; discount fields read-only (server computed)
    promo_code = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Order
        fields = ['id', 'user', 'comic', 'purchase_date', 'buyer_name', 'email', 'mobile',
                  'address', 'pin_code', 'promo_code', 'discount_applied', 'final_price']
        read_only_fields = ['id', 'purchase_date', 'discount_applied', 'final_price']

    def validate_buyer_name(self, value):
        if not value.strip():
            raise ValidationError("Buyer name cannot be empty.")
        if len(value) > 255:
            raise ValidationError("Buyer name must not exceed 255 characters.")
        return value

    def validate_email(self, value):
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value):
            raise ValidationError("Invalid email format.")
        return value

    def validate_mobile(self, value):
        # Allow +91... etc
        if not re.match(r'^\+?[0-9]{7,15}$', value):
            raise ValidationError("Invalid mobile number format.")
        return value

    def validate_pin_code(self, value):
        if not re.match(r'^\d{6}$', value):
            raise ValidationError("Pin code must be a 6-digit number.")
        return value

    def validate(self, data):
        comic = data['comic']
        if comic.stock_quantity <= 0:
            raise ValidationError("Comic is out of stock.")
        return data


class ReviewSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False)

    class Meta:
        model = Review
        fields = ['id', 'user', 'comic', 'rating', 'comment', 'created_at']
        read_only_fields = ['id', 'created_at']

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
        user = self.context['request'].user if 'request' in self.context else None
        if not user or not Order.objects.filter(user=user, comic=data['comic']).exists():
            raise ValidationError("You can only review a comic you have purchased.")
        return data


class WishlistSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(queryset=CustomUser.objects.all(), required=False,
                                              default=serializers.CurrentUserDefault())

    class Meta:
        model = Wishlist
        fields = ['id', 'user', 'comic', 'added_at']
        read_only_fields = ['id', 'added_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].required = False


class PromotionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Promotion
        fields = [
            'id', 'title', 'code', 'discount_type', 'discount_value', 'terms',
            'genre', 'comic', 'max_uses', 'per_user_limit', 'min_order_amount',
            'used_count', 'start_date', 'end_date'
        ]
        read_only_fields = ['id', 'used_count']

    def validate_code(self, value):
        if value in (None, ''):
            return None
        v = value.strip().upper()
        if not re.match(r'^[A-Z0-9_-]{3,32}$', v):
            raise ValidationError("Code must be 3-32 chars, uppercase letters, digits, _ or -.")
        return v

    def validate(self, data):
        if data['start_date'] >= data['end_date']:
            raise ValidationError("Start date must be before end date.")
        if data['discount_type'] == 'percentage':
            if data['discount_value'] < 0 or data['discount_value'] > 100:
                raise ValidationError("Percentage must be between 0 and 100.")
        else:
            if data['discount_value'] < 0:
                raise ValidationError("Fixed discount must be >= 0.")
        return data


# NotificationPreference and RestockNotification serializers removed: corresponding models do not exist in storeDesk.models