from django.urls import path
from .views import FavouriteViewSet

urlpatterns = [
    # List + Create
    path(
        'favourites/',
        FavouriteViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='favourite-list-create',
    ),

    # GET /favourites/status/{comic_type}/{comic_id}/
    # IMPORTANT: put this BEFORE the generic remove route
    path(
        'favourites/status/<str:comic_type>/<path:comic_id>/',
        FavouriteViewSet.as_view({'get': 'status'}),
        name='favourite-status',
    ),

    # DELETE /favourites/{comic_type}/{comic_id}/
    path(
        'favourites/<str:comic_type>/<path:comic_id>/',
        FavouriteViewSet.as_view({'delete': 'remove'}),
        name='favourite-remove',
    ),

    # GET /favourites/search/?q=...&type=...
    path(
        'favourites/search/',
        FavouriteViewSet.as_view({'get': 'search'}),
        name='favourite-search',
    ),
]