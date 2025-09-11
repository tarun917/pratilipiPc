from .models import CustomUser, Address
from rest_framework import serializers
from django.core.exceptions import ValidationError
from communityDesk.models import Follow


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['profile_image', 'about', 'coin_count', 'email', 'mobile_number', 'date_joined']
        extra_kwargs = {
            'coin_count': {'read_only': True},
            'email': {'required': False},
            'mobile_number': {'required': False},
            'date_joined': {'read_only': True},
        }

    def update(self, instance, validated_data):
        instance.profile_image = validated_data.get('profile_image', instance.profile_image)
        instance.about = validated_data.get('about', instance.about)
        instance.email = validated_data.get('email', instance.email)
        instance.mobile_number = validated_data.get('mobile_number', instance.mobile_number)
        instance.save()
        return instance

    def validate_profile_image(self, value):
        if value:
            if value.size > 5 * 1024 * 1024:
                raise ValidationError("Image size must not exceed 5MB.")
            if not value.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise ValidationError("Only JPG, JPEG, and PNG formats are allowed.")
        return value

    def validate_about(self, value):
        if value and len(value.split()) > 256:
            raise ValidationError("About section must not exceed 256 words.")
        return value


class ProfileImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['profile_image']

    def validate_profile_image(self, value):
        if value:
            if value.size > 5 * 1024 * 1024:
                raise ValidationError("Image size must not exceed 5MB.")
            if not value.name.lower().endswith(('.jpg', '.jpeg', '.png')):
                raise ValidationError("Only JPG, JPEG, and PNG formats are allowed.")
        return value

    def update(self, instance, validated_data):
        instance.profile_image = validated_data.get('profile_image', instance.profile_image)
        instance.save()
        return instance


# Public user details (limited fields)
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name', 'profile_image', 'badge']
        extra_kwargs = {
            'profile_image': {'read_only': True},
        }


# Address serializers (owner-scoped usage via context['request'])
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'name', 'mobile_number', 'line1', 'line2', 'landmark',
            'city', 'state', 'pincode', 'country', 'address_type',
            'is_default', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Attach current user; viewset must pass context={'request': request}
        request = self.context.get('request')
        if not request or not request.user or not request.user.is_authenticated:
            raise ValidationError("Authentication required.")
        validated_data['user'] = request.user
        return super().create(validated_data)

    def validate_mobile_number(self, value):
        # Basic guard; extend with regex per region if needed
        if value and len(value) > 15:
            raise ValidationError("Invalid mobile number.")
        return value

    def validate_pincode(self, value):
        if value and len(value) > 20:
            raise ValidationError("Invalid pincode.")
        return value


# profileDesk/short_serializers.py (kept here for convenience)

class ShortUserSerializer(serializers.ModelSerializer):
    my_follow_id = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'profile_image', 'badge', 'my_follow_id']
        extra_kwargs = {
            'profile_image': {'read_only': True},
        }
        read_only_fields = ['id', 'username', 'profile_image', 'badge']

    def get_my_follow_id(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if request.user.id == obj.id:
                return None
            rel = Follow.objects.filter(follower=request.user, following=obj).values('id').first()
            return rel['id'] if rel else None
        return None


class SearchUserSerializer(serializers.ModelSerializer):
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name', 'profile_image', 'badge', 'is_following']

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            if request.user == obj:
                return False
            return Follow.objects.filter(follower=request.user, following=obj).exists()
        return False