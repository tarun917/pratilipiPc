from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SearchFilterViewSet

router = DefaultRouter()
router.register(r'filter', SearchFilterViewSet, basename='search-filter')

urlpatterns = router.urls