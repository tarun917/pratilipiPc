from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ProfileViewSet, UserViewSet, AddressViewSet

# Router for read-only public users (currently behind IsAuthenticated in views)
router_users = DefaultRouter()
router_users.register(r'users', UserViewSet, basename='user')  # /users/

# Nested router for profile-specific resources
router_profile = DefaultRouter()
router_profile.register(r'addresses', AddressViewSet, basename='profile-address')  # /profile/addresses/

profile_patterns = [
    path('profile/picture/', ProfileViewSet.as_view({'post': 'upload_image'}), name='profile-picture'),
    path('profile/', ProfileViewSet.as_view({'get': 'retrieve', 'patch': 'update'}), name='profile-retrieve-update'),
    path('profile/', include(router_profile.urls)),
]

urlpatterns = profile_patterns + router_users.urls