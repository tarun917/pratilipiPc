from django.db.models import Q
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import NotificationModel, DeviceToken
from .serializers import NotificationSerializer, DeviceTokenSerializer


class NotificationPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class IsAuthenticatedOrReadOnlyBroadcast(permissions.IsAuthenticated):
    pass


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticatedOrReadOnlyBroadcast]
    pagination_class = NotificationPagination
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["notification_type", "comic_type", "related_tab"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        user = self.request.user
        qs = NotificationModel.objects.filter(Q(user=user) | Q(user__isnull=True))

        is_read = self.request.query_params.get("is_read")
        if is_read is not None:
            if is_read.lower() in ("1", "true", "yes"):
                qs = qs.filter(read_at__isnull=False)
            elif is_read.lower() in ("0", "false", "no"):
                qs = qs.filter(read_at__isnull=True)

        before = self.request.query_params.get("before")
        after = self.request.query_params.get("after")
        if before:
            dt = parse_datetime(before)
            if dt:
                qs = qs.filter(created_at__lt=dt)
        if after:
            dt = parse_datetime(after)
            if dt:
                qs = qs.filter(created_at__gt=dt)

        return qs

    @action(detail=False, methods=["get"], url_path="unread_count")
    def unread_count(self, request, *args, **kwargs):
        user = request.user
        count = NotificationModel.objects.filter(Q(user=user) | Q(user__isnull=True), read_at__isnull=True).count()
        return Response({"unread_count": count})

    @action(detail=True, methods=["post"], url_path="mark_read")
    def mark_read(self, request, pk=None, *args, **kwargs):
        notif = self.get_object()
        if notif.user_id is None:
            return Response(
                {"detail": "Broadcast notification cannot be marked as read individually."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if notif.user_id != request.user.id:
            return Response(status=status.HTTP_403_FORBIDDEN)
        notif.mark_read()
        return Response({"status": "ok", "id": notif.id, "read_at": notif.read_at})

    @action(detail=False, methods=["post"], url_path="read_all")
    def read_all(self, request, *args, **kwargs):
        updated = NotificationModel.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response({"status": "ok", "updated": updated})


class DeviceTokenRegisterView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        token = data["token"]

        # Upsert by token; token unique hai
        obj, created = DeviceToken.objects.get_or_create(
            token=token,
            defaults={
                "user": request.user,
                "platform": data["platform"],
                "app_version": data.get("app_version"),
                "locale": data.get("locale"),
                "is_active": True,
            },
        )
        if not created:
            # Reassign to current user (device handover), and refresh fields
            obj.user = request.user
            obj.platform = data["platform"]
            obj.app_version = data.get("app_version")
            obj.locale = data.get("locale")
            obj.is_active = True
            obj.save(update_fields=["user", "platform", "app_version", "locale", "is_active", "last_seen_at"])

        return Response(
            {"status": "ok", "created": created, "id": obj.id},
            status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED,
        )


class DeviceTokenDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, token: str):
        try:
            obj = DeviceToken.objects.get(token=token)
        except DeviceToken.DoesNotExist:
            return Response(status=status.HTTP_204_NO_CONTENT)
        # Ensure ownership
        if obj.user_id != request.user.id:
            return Response(status=status.HTTP_404_NOT_FOUND)
        # Soft-deactivate
        obj.is_active = False
        obj.save(update_fields=["is_active", "last_seen_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)