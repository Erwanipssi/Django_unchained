from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import BountyMission, Hunter, WantedPerson
from .permissions import (
    CanManageBountyMission,
    CanManageWantedPerson,
    CanViewHunter,
)
from .serializers import (
    BountyMissionSerializer,
    HunterRegistrationSerializer,
    HunterSerializer,
    SheriffRegistrationSerializer,
    SheriffSerializer,
    WantedPersonSerializer,
)


class WantedPersonViewSet(viewsets.ModelViewSet):
    queryset = WantedPerson.objects.all()
    serializer_class = WantedPersonSerializer
    permission_classes = [CanManageWantedPerson]


class BountyMissionViewSet(viewsets.ModelViewSet):
    queryset = BountyMission.objects.all()
    serializer_class = BountyMissionSerializer
    permission_classes = [CanManageBountyMission]

    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        mission = self.get_object()
        hunter = getattr(request.user, "hunter_profile", None)
        result = request.data.get("result")

        if hunter is None:
            return Response(
                {"detail": "Seul un chasseur peut réclamer une prime."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if mission.status != BountyMission.Status.OPEN:
            return Response(
                {"detail": "Cette prime n'est plus disponible."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if mission.wanted_person.status != WantedPerson.Status.WANTED:
            return Response(
                {"detail": "Cette personne n'est plus recherchée."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if result not in BountyMission.ClaimedResult.values:
            return Response(
                {"detail": "Le résultat doit être CAPTURED ou KILLED."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mission.hunter = hunter
        mission.claimed_result = result
        mission.claimed_at = timezone.now()
        mission.status = BountyMission.Status.PENDING_VERIFICATION
        mission.save()

        return Response(self.get_serializer(mission).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="validate-result",
    )
    def validate_result(self, request, pk=None):
        mission = self.get_object()
        sheriff = getattr(request.user, "sheriff_profile", None)

        if sheriff is None:
            return Response(
                {"detail": "Seul un shérif peut valider un résultat."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if (
            mission.status != BountyMission.Status.PENDING_VERIFICATION
            or mission.claimed_result not in BountyMission.ClaimedResult.values
        ):
            return Response(
                {"detail": "Cette mission n'attend pas de vérification."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            mission.received_by = sheriff
            mission.received_at = timezone.now()
            mission.status = mission.claimed_result
            mission.save()

            if mission.claimed_result == BountyMission.ClaimedResult.CAPTURED:
                mission.wanted_person.status = WantedPerson.Status.CAPTURED
            else:
                mission.wanted_person.status = WantedPerson.Status.DEAD
            mission.wanted_person.save()

        return Response(self.get_serializer(mission).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="reject-result",
    )
    def reject_result(self, request, pk=None):
        mission = self.get_object()
        sheriff = getattr(request.user, "sheriff_profile", None)

        if sheriff is None:
            return Response(
                {"detail": "Seul un shérif peut refuser un résultat."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if mission.status != BountyMission.Status.PENDING_VERIFICATION:
            return Response(
                {"detail": "Cette mission n'attend pas de vérification."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        mission.hunter = None
        mission.claimed_result = None
        mission.claimed_at = None
        mission.status = BountyMission.Status.OPEN
        mission.save()

        return Response(self.get_serializer(mission).data)


class HunterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Hunter.objects.all()
    serializer_class = HunterSerializer
    permission_classes = [CanViewHunter]

    @action(detail=False, methods=["get"])
    def me(self, request):
        hunter = getattr(request.user, "hunter_profile", None)

        if hunter is None:
            return Response(
                {"detail": "Cet utilisateur n'est pas un chasseur."},
                status=status.HTTP_403_FORBIDDEN,
            )

        return Response(self.get_serializer(hunter).data)


class RegistrationViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminUser]

    @action(detail=False, methods=["post"])
    def hunter(self, request):
        serializer = HunterRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        hunter = serializer.save()
        return Response(
            HunterSerializer(hunter).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def sheriff(self, request):
        serializer = SheriffRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        sheriff = serializer.save()
        return Response(
            SheriffSerializer(sheriff).data,
            status=status.HTTP_201_CREATED,
        )
