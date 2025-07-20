from .models import CustomUser
from rest_framework import serializers
from django.core.exceptions import ValidationError

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
    

# New: Serializer for public user details (limited fields)
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name', 'profile_image', 'badge']  # Public fields only
        extra_kwargs = {
            'profile_image': {'read_only': True},
        }


# profileDesk/short_serializers.py

from rest_framework import serializers
from .models import CustomUser

class ShortUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'profile_image', 'badge']
        extra_kwargs = {
            'profile_image': {'read_only': True},
        }
        read_only_fields = ['id', 'username', 'profile_image', 'badge']



class SearchUserSerializer(serializers.ModelSerializer):
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'full_name', 'profile_image', 'badge', 'is_following']

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # User cannot follow themselves
            if request.user == obj:
                return False
            from communityDesk.models import Follow
            return Follow.objects.filter(follower=request.user, following=obj).exists()
        return False
