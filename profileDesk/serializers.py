from rest_framework import serializers
import re
from django.core.exceptions import ValidationError

from .models import CustomUser
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.tokens import RefreshToken

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['username', 'full_name', 'email', 'mobile_number', 'password', 'terms_accepted']
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
        }

    def validate_username(self, value):
        if not value.strip():
            raise serializers.ValidationError("Username cannot be empty.")
        if CustomUser.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        if not re.match(r'^[A-Za-z0-9_.-]+$', value):
            raise serializers.ValidationError("Username can only contain letters, numbers, underscores, dots, or hyphens.")
        return value

    def validate_full_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Full name cannot be empty.")
        cleaned_value = re.sub(r'[^A-Za-z\s-]', '', value)
        if cleaned_value != value:
            raise serializers.ValidationError("Full name can only contain letters, spaces, or hyphens.")
        return cleaned_value

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value.lower()

    def validate_mobile_number(self, value):
        if not value.startswith('+'):
            value = '+91' + value
        if not re.match(r'^\+[1-9]\d{1,14}$', value):
            raise serializers.ValidationError("Invalid mobile number format (e.g., +919406702569).")
        if CustomUser.objects.filter(mobile_number=value).exists():
            raise serializers.ValidationError("This mobile number is already registered.")
        return value

    def validate_terms_accepted(self, value):
        if not value:
            raise serializers.ValidationError("You must agree to the terms and conditions.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$', value):
            raise serializers.ValidationError("Password must contain at least 8 characters, including letters and numbers.")
        return value

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        username_or_email = data.get('username_or_email').lower()
        password = data.get('password')

        user = None
        if '@' in username_or_email:
            try:
                user = CustomUser.objects.get(email=username_or_email)
            except CustomUser.DoesNotExist:
                pass
        else:
            try:
                user = CustomUser.objects.get(username=username_or_email)
            except CustomUser.DoesNotExist:
                pass

        if user is None or not user.check_password(password):
            raise serializers.ValidationError("Invalid username/email or password.")

        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")

        refresh = RefreshToken.for_user(user)
        return {
            'token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'userId': user.id,
            'username': user.username
        }

class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['profile_image', 'about', 'coin_count']
        extra_kwargs = {
            'coin_count': {'read_only': True},
        }

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

    def update(self, instance, validated_data):
        instance.profile_image = validated_data.get('profile_image', instance.profile_image)
        instance.about = validated_data.get('about', instance.about)
        instance.save()
        return instance

class ProfileImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['profile_image']

    def validate_profile_image(self, value):
        if value.size > 5 * 1024 * 1024:
            raise ValidationError("Image size must not exceed 5MB.")
        if not value.name.lower().endswith(('.jpg', '.jpeg', '.png')):
            raise ValidationError("Only JPG, JPEG, and PNG formats are allowed.")
        return value

    def update(self, instance, validated_data):
        instance.profile_image = validated_data.get('profile_image', instance.profile_image)
        instance.save()
        return instance