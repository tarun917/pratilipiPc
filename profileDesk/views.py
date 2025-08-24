from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from .models import CustomUser
from .serializers import CustomUserSerializer, ProfileUpdateSerializer, ProfileImageSerializer


class ProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = (MultiPartParser, FormParser)

    def list(self, request):
        return Response({"error": "List view not allowed"}, status=status.HTTP_403_FORBIDDEN)

    def retrieve(self, request, pk=None):
        user = request.user
        profile_image_url = user.profile_image.url if user.profile_image else None
        if profile_image_url and not profile_image_url.startswith('http'):
            profile_image_url = request.build_absolute_uri(profile_image_url)
        return Response({
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "mobile_number": user.mobile_number,
            "profile_image": profile_image_url,
            "about": user.about,
            "coin_count": user.coin_count,
            "badge": user.badge,
        }, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        user = request.user
        serializer = ProfileUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def upload_image(self, request):
        user = request.user
        serializer = ProfileImageSerializer(user, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Public user details by ID (read-only)
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]