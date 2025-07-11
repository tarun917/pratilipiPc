from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import SearchFilterModel
from .serializers import SearchFilterSerializer

class SearchFilterViewSet(viewsets.ModelViewSet):
    queryset = SearchFilterModel.objects.all()
    serializer_class = SearchFilterSerializer
    permission_classes = [IsAuthenticated]