from rest_framework import viewsets, permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CoinModel
from .serializers import CoinSerializer


class CoinViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only wallet model view.
    - No client-controlled writes.
    - Queryset is scoped to the authenticated user.
    """
    serializer_class = CoinSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CoinModel.objects.filter(user=self.request.user)


class BalanceView(APIView):
    """
    GET /api/coins/balance/
    Returns: { "balance": <int> } from CustomUser.coin_count (source of truth).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({"balance": int(user.coin_count or 0)})