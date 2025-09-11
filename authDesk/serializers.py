from rest_framework import serializers
import re
from django.core.exceptions import ValidationError
from profileDesk.models import CustomUser
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
        # Add mobile number validation if needed
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
