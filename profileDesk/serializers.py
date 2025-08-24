from .models import CustomUser
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


# New: Serializer for public user details (limited fields)
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name', 'profile_image', 'badge']  # Public fields only
        extra_kwargs = {
            'profile_image': {'read_only': True},
        }


# profileDesk/short_serializers.py

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