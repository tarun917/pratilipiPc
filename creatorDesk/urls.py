from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CreatorDeskViewSet

router = DefaultRouter()
router.register(r'creatordesk', CreatorDeskViewSet, basename='creatordesk')

urlpatterns = router.urls