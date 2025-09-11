from rest_framework.routers import DefaultRouter
from .views import MotionComicViewSet, EpisodeViewSet

router = DefaultRouter()
router.register(r'motioncomic', MotionComicViewSet, basename='motioncomic')
router.register(r'motioncomic/episode', EpisodeViewSet, basename='motion-episode')

urlpatterns = router.urls