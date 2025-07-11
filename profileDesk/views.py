import json
from django.http import JsonResponse
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
import logging

from .models import CustomUser
from .serializers import UserSerializer, LoginSerializer, ProfileUpdateSerializer, ProfileImageSerializer

logger = logging.getLogger(__name__)

class AuthViewSet(viewsets.GenericViewSet):
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'register':
            return UserSerializer
        elif self.action == 'login':
            return LoginSerializer
        return None

    def create(self, request, *args, **kwargs):
        if request.path.endswith('signup/'):
            return self.register(request)
        elif request.path.endswith('login/'):
            return self.login(request)
        return Response({"error": "Invalid endpoint"}, status=status.HTTP_400_BAD_REQUEST)

    def register(self, request):
        logger.debug(f"Register attempt with data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                refresh = RefreshToken.for_user(user)
                logger.info(f"User registered: {user.username}")
                return Response({
                    "token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "userId": user.id,
                    "username": user.username
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                logger.error(f"Registration failed: {str(e)}")
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        logger.error(f"Registration failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def login(self, request):
        logger.debug(f"Login attempt with data: {request.data}")
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user_data = serializer.validated_data
            logger.info(f"User logged in: {user_data['username']}")
            return Response(user_data, status=status.HTTP_200_OK)
        logger.error(f"Login failed: {serializer.errors}")
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def logout_view(request):
    if request.method == 'POST':
        logger.debug(f"Logout attempt with raw data: {request.body}")
        try:
            data = json.loads(request.body.decode('utf-8'))
            refresh_token = data.get('refresh_token')
            if not refresh_token:
                logger.error("No refresh token provided in JSON data")
                return JsonResponse({"error": "Refresh token is required"}, status=400)
            logger.debug(f"Validating token: {refresh_token}")
            token = RefreshToken(refresh_token)
            token.blacklist()
            logger.info(f"Token blacklisted successfully: {refresh_token}")
            return JsonResponse({"message": "Logged out successfully"}, status=200)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {str(e)}")
            return JsonResponse({"error": "Invalid JSON format"}, status=400)
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            return JsonResponse({"error": f"Invalid token: {str(e)}"}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)

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