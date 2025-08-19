from django.urls import path
from .views import FavouriteViewSet

urlpatterns = [
    # List + Create match karein
    path(
        'favourites/',
        FavouriteViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='favourite-list-create',
    ),

    # DELETE /favourites/{comic_type}/{comic_id}/
    # comic_type: digital|motion (aliases allowed in view), comic_id: UUID ya koi bhi string
    path(
        'favourites/<str:comic_type>/<path:comic_id>/',
        FavouriteViewSet.as_view({'delete': 'remove'}),
        name='favourite-remove',
    ),

    # GET /favourites/status/{comic_type}/{comic_id}/
    path(
        'favourites/status/<str:comic_type>/<path:comic_id>/',
        FavouriteViewSet.as_view({'get': 'status'}),
        name='favourite-status',
    ),

    # GET /favourites/search/?q=...&type=...
    path(
        'favourites/search/',
        FavouriteViewSet.as_view({'get': 'search'}),
        name='favourite-search',
    ),
]