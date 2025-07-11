from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import HomeTabConfig
from favouriteDesk.models import FavouriteModel
from favouriteDesk.serializers import FavouriteSerializer

class HomeContentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
    
        user = request.user
        favourites = FavouriteModel.objects.filter(user=user)
        serializer = FavouriteSerializer(favourites, many=True)
        return Response(serializer.data)