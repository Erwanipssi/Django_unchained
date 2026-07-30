from django.urls import path
from rest_framework.routers import DefaultRouter

from .api_views import (
    BountyMissionViewSet,
    HunterViewSet,
    RegistrationViewSet,
    WantedPersonViewSet,
    me,
)


router = DefaultRouter()
router.register("wanted-persons", WantedPersonViewSet)
router.register("missions", BountyMissionViewSet)
router.register("hunters", HunterViewSet)
router.register("register", RegistrationViewSet, basename="register")

urlpatterns = [
    path("me/", me, name="api-me"),
] + router.urls
