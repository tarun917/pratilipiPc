from django.urls import path
from .views import AuthViewSet, logout_view
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('signup/', AuthViewSet.as_view({'post': 'register'}), name='auth-signup'),
    path('login/', AuthViewSet.as_view({'post': 'login'}), name='auth-login'),
    path('logout/', logout_view, name='auth-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
