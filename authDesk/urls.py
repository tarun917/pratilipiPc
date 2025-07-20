from django.urls import path
from .views import AuthViewSet, logout_view

urlpatterns = [
    path('signup/', AuthViewSet.as_view({'post': 'register'}), name='auth-signup'),
    path('login/', AuthViewSet.as_view({'post': 'login'}), name='auth-login'),
    path('logout/', logout_view, name='auth-logout'),
]
