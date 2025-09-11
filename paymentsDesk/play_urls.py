from django.urls import path
from .views import PlayVerifyView

urlpatterns = [
    path('verify/', PlayVerifyView.as_view(), name='play-verify'),
]