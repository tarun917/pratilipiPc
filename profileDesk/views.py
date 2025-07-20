
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .models import CustomUser
from .serializers import CustomUserSerializer, ProfileUpdateSerializer, ProfileImageSerializer

class ProfileViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response({"error": "List view not allowed"}, status=status.HTTP_403_FORBIDDEN)

    def retrieve(self, request):
        user = request.user
        return Response({
            "username": user.username,
            "full_name": user.full_name,
            "email": user.email,
            "mobile_number": user.mobile_number,
            "profile_image": user.profile_image.url if user.profile_image else None,
            "about": user.about,
            "coin_count": user.coin_count,
            "badge": user.badge,  # Assuming badge is a field in CustomUser
        }, status=status.HTTP_200_OK)

    def update(self, request):
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
    


# New: UserViewSet for getting public user details by ID
class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]  # Authenticated only

    def retrieve(self, request, pk=None):
        user = self.get_object()
        serializer = self.get_serializer(user)
        return Response(serializer.data)