from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PostViewSet, CommentViewSet, PollViewSet, VoteViewSet, FollowViewSet, LikeViewSet, SearchViewSet

router = DefaultRouter()
router.register(r'posts', PostViewSet)
router.register(r'posts/(?P<post_pk>\d+)/comments', CommentViewSet)
router.register(r'posts/(?P<post_pk>\d+)/polls', PollViewSet)
router.register(r'polls/(?P<poll_pk>\d+)/votes', VoteViewSet)
router.register(r'users/(?P<user_pk>\d+)/follow', FollowViewSet, basename='follow')
router.register(r'posts/(?P<post_pk>\d+)/likes', LikeViewSet)
router.register(r'search', SearchViewSet, basename='search')

urlpatterns = router.urls + [
    path('posts/<int:pk>/share/', PostViewSet.as_view({'post': 'share'}), name='post-share'),
    path('posts/<int:pk>/copy-link/', PostViewSet.as_view({'get': 'copy_link'}), name='post-copy-link'),
    path('users/<int:user_pk>/follow-status/', FollowViewSet.as_view({'get': 'follow_status'}), name='follow-status'),
    path('users/<int:user_pk>/followers/', FollowViewSet.as_view({'get': 'followers'}), name='followers'),
    path('users/<int:user_pk>/following/', FollowViewSet.as_view({'get': 'following'}), name='following'),
]