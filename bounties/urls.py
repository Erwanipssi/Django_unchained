from rest_framework.routers import DefaultRouter

from .api_views import (
    BountyMissionViewSet,
    HunterViewSet,
    RegistrationViewSet,
    WantedPersonViewSet,
)


router = DefaultRouter()
router.register("wanted-persons", WantedPersonViewSet)
router.register("missions", BountyMissionViewSet)
router.register("hunters", HunterViewSet)
router.register("register", RegistrationViewSet, basename="register")

urlpatterns = router.urls
