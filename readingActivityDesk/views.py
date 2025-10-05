from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import ReadingActivity
from .serializers import (
    InProgressItemSerializer, FinishedItemSerializer, ProgressWriteSerializer
)

FINISH_THRESHOLD = 95.0

class InProgressListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = InProgressItemSerializer

    def get_queryset(self):
        qs = ReadingActivity.objects.filter(user=self.request.user, finished_at__isnull=True)
        type_q = self.request.query_params.get("type")
        if type_q in ("digital", "motion"):
            qs = qs.filter(type=type_q)
        # exclude snoozed
        qs = qs.exclude(snoozed_until__gt=timezone.now().date())
        return qs.order_by("-last_read_at")

class FinishedListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = FinishedItemSerializer

    def get_queryset(self):
        qs = ReadingActivity.objects.filter(user=self.request.user, finished_at__isnull=False)
        type_q = self.request.query_params.get("type")
        if type_q in ("digital", "motion"):
            qs = qs.filter(type=type_q)
        return qs.order_by("-finished_at")

class ProgressUpsertView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        s = ProgressWriteSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        data = s.validated_data

        obj, _ = ReadingActivity.objects.get_or_create(
            user=request.user,
            type=data["type"],
            comic_id=data["comic_id"],
            defaults={"episode_id": data.get("episode_id")}
        )
        # update fields
        obj.episode_id = data.get("episode_id", obj.episode_id)
        obj.progress_percent = float(data["progress_percent"])
        obj.position_ms = data.get("position_ms", obj.position_ms)
        obj.comic_title = data.get("comic_title", obj.comic_title)
        obj.episode_label = data.get("episode_label", obj.episode_label)
        obj.cover_url = data.get("cover_url", obj.cover_url)

        if obj.progress_percent >= FINISH_THRESHOLD and obj.finished_at is None:
            obj.finished_at = timezone.now()

        obj.save()
        return Response({"ok": True}, status=status.HTTP_200_OK)

class MarkFinishedView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request):
        t = request.data.get("type")
        cid = request.data.get("comic_id")
        if t not in ("digital", "motion") or not cid:
            return Response({"detail": "Invalid payload"}, status=400)
        obj, _ = ReadingActivity.objects.get_or_create(
            user=request.user, type=t, comic_id=cid
        )
        obj.progress_percent = 100.0
        obj.finished_at = timezone.now()
        obj.save()
        return Response({"ok": True}, status=200)

class RemoveItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    def delete(self, request):
        t = request.data.get("type")
        cid = request.data.get("comic_id")
        if t not in ("digital", "motion") or not cid:
            return Response({"detail": "Invalid payload"}, status=400)
        ReadingActivity.objects.filter(user=request.user, type=t, comic_id=cid).delete()
        return Response(status=204)