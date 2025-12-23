from django.urls import path
from .views import SignupView, LoginView, logout_view
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('signup/', SignupView.as_view(), name='auth-signup'),
    path('login/', LoginView.as_view(), name='auth-login'),
    path('logout/', logout_view, name='auth-logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
]
