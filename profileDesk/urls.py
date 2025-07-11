from django.urls import path, include
from .views import AuthViewSet, ProfileViewSet, logout_view

auth_patterns = [
    path('signup/', AuthViewSet.as_view({'post': 'register'}), name='auth-signup'),
    path('login/', AuthViewSet.as_view({'post': 'login'}), name='auth-login'),
    path('logout/', logout_view, name='auth-logout'),
]

profile_patterns = [
    path('profile/picture/', ProfileViewSet.as_view({'post': 'upload_image'}), name='profile-picture'),
    path('profile/', ProfileViewSet.as_view({'get': 'retrieve', 'patch': 'update'}), name='profile-retrieve-update'),
]

urlpatterns = [
    path('auth/', include(auth_patterns)),
    path('', include(profile_patterns)),
]