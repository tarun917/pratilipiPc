from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, DeviceTokenRegisterView, DeviceTokenDeleteView

router = DefaultRouter()
router.register(r"notifications", NotificationViewSet, basename="notifications")

urlpatterns = [
    path("", include(router.urls)),
    path("notify/device/", DeviceTokenRegisterView.as_view(), name="device-register"),
    path("notify/device/<str:token>/", DeviceTokenDeleteView.as_view(), name="device-delete"),
]