from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .models import CarouselItemModel
from .serializers import CarouselItemSerializer


class CarouselItemViewSet(viewsets.ModelViewSet):
    queryset = CarouselItemModel.objects.all().order_by('order')
    serializer_class = CarouselItemSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action == 'list' or self.action == 'retrieve':
            return [AllowAny()]
        return super().get_permissions()

    def list(self, request):
        type_filter = request.query_params.get('type', 'digital')
        if type_filter not in ('digital', 'motion'):
            type_filter = 'digital'
        queryset = self.queryset.filter(type=type_filter)[:10]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)