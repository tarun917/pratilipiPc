from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CoinModel
from .serializers import CoinSerializer
from django.shortcuts import get_object_or_404

class CoinViewSet(viewsets.ModelViewSet):
    queryset = CoinModel.objects.all()
    serializer_class = CoinSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        amount = int(self.request.data.get('amount', 0))
        user = self.request.user
        coin_instance, created = CoinModel.objects.get_or_create(user=user, defaults={'balance': 0})
        coin_instance.balance = coin_instance.balance + amount  # Explicitly set new balance
        coin_instance.save()
        serializer.instance = coin_instance
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        amount = int(request.data.get('amount', 0))
        instance.balance = instance.balance + amount  # Explicitly set new balance
        instance.save()
        return Response(self.get_serializer(instance).data)