from django.urls import path
from .views import FavouriteViewSet

urlpatterns = [
    path('favourites/', FavouriteViewSet.as_view({'get': 'list', 'post': 'add'}), name='favourite-list-add'),
    path('favourites/<int:comic_id>/', FavouriteViewSet.as_view({'delete': 'remove'}), name='favourite-remove'),  # Changed comicId to comic_id
    path('favourites/status/<int:comic_id>/', FavouriteViewSet.as_view({'get': 'status'}), name='favourite-status'),
    path('favourites/search/', FavouriteViewSet.as_view({'get': 'search'}), name='favourite-search'),
]