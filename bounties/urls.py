from rest_framework.routers import DefaultRouter

from .api_views import BountyMissionViewSet, WantedPersonViewSet


router = DefaultRouter()
router.register("wanted-persons", WantedPersonViewSet)
router.register("missions", BountyMissionViewSet)

urlpatterns = router.urls
