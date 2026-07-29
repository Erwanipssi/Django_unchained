from rest_framework import viewsets

from .models import BountyMission, WantedPerson
from .serializers import BountyMissionSerializer, WantedPersonSerializer


class WantedPersonViewSet(viewsets.ModelViewSet):
    queryset = WantedPerson.objects.all()
    serializer_class = WantedPersonSerializer


class BountyMissionViewSet(viewsets.ModelViewSet):
    queryset = BountyMission.objects.all()
    serializer_class = BountyMissionSerializer
