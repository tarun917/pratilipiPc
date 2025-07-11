from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CarouselItemModel
from .serializers import CarouselItemSerializer

class CarouselItemViewSet(viewsets.ModelViewSet):
    queryset = CarouselItemModel.objects.all().order_by('order')
    serializer_class = CarouselItemSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request):
        type_filter = request.query_params.get('type', 'digital')
        queryset = self.queryset.filter(type=type_filter)[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)