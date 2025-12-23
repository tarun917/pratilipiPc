import json
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from django.views.decorators.csrf import csrf_exempt
import logging

from profileDesk.models import CustomUser
from .serializers import UserSerializer, LoginSerializer

logger = logging.getLogger(__name__)

class SignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.save()
                refresh = RefreshToken.for_user(user)
                return Response({
                    "token": str(refresh.access_token),
                    "refresh_token": str(refresh),
                    "userId": user.id,
                    "username": user.username
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user_data = serializer.validated_data
            return Response(user_data, status=status.HTTP_200_OK)
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
from django.shortcuts import render

# Create your views here.
