from django.urls import path, include
from .views import ProfileViewSet, UserViewSet
from rest_framework.routers import DefaultRouter


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')  # New: /api/users/


profile_patterns = [
    path('profile/picture/', ProfileViewSet.as_view({'post': 'upload_image'}), name='profile-picture'),
    path('profile/', ProfileViewSet.as_view({'get': 'retrieve', 'patch': 'update'}), name='profile-retrieve-update'),
]

urlpatterns = profile_patterns + router.urls