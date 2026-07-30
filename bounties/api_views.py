from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import BountyMission, Hunter, WantedPerson
from .permissions import (
    CanManageBountyMission,
    CanManageWantedPerson,
    CanViewHunter,
)
from .serializers import (
    BountyMissionSerializer,
    ClaimMissionSerializer,
    HunterRegistrationSerializer,
    HunterSerializer,
    SheriffRegistrationSerializer,
    SheriffSerializer,
    WantedPersonSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    user = request.user
    data = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
    }
    if hasattr(user, "sheriff_profile"):
        data["sheriff_id"] = user.sheriff_profile.id
        data["city"] = user.sheriff_profile.city
    if hasattr(user, "hunter_profile"):
        data["hunter_id"] = user.hunter_profile.id
        data["nickname"] = user.hunter_profile.nickname
    return Response(data)


class WantedPersonViewSet(viewsets.ModelViewSet):
    queryset = WantedPerson.objects.all()
    serializer_class = WantedPersonSerializer
    permission_classes = [CanManageWantedPerson]


class BountyMissionViewSet(viewsets.ModelViewSet):
    queryset = BountyMission.objects.select_related(
        "wanted_person",
        "hunter",
        "commissioned_by",
        "received_by",
    )
    serializer_class = BountyMissionSerializer
    permission_classes = [CanManageBountyMission]

    def _get_locked_mission(self, pk):
        queryset = self.filter_queryset(
            BountyMission.objects.all()
        ).select_for_update()
        mission = get_object_or_404(queryset, pk=pk)
        self.check_object_permissions(self.request, mission)
        return mission

    def perform_create(self, serializer):
        serializer.save(commissioned_by=self.request.user.sheriff_profile)

    def perform_update(self, serializer):
        if serializer.instance.status != BountyMission.Status.OPEN:
            raise serializers.ValidationError(
                "Seule une mission ouverte peut être modifiée."
            )
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        with transaction.atomic():
            mission = self._get_locked_mission(kwargs["pk"])
            if mission.status != BountyMission.Status.OPEN:
                return Response(
                    {"detail": "Seule une mission ouverte peut être annulée."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            mission.status = BountyMission.Status.CANCELLED
            mission.save(update_fields=["status"])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"])
    def claim(self, request, pk=None):
        input_serializer = ClaimMissionSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            mission = self._get_locked_mission(pk)

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

            mission.hunter = request.user.hunter_profile
            mission.claimed_result = input_serializer.validated_data["result"]
            mission.claimed_at = timezone.now()
            mission.status = BountyMission.Status.PENDING_VERIFICATION
            mission.save(
                update_fields=[
                    "hunter",
                    "claimed_result",
                    "claimed_at",
                    "status",
                ]
            )

        return Response(self.get_serializer(mission).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="validate-result",
    )
    def validate_result(self, request, pk=None):
        with transaction.atomic():
            mission = self._get_locked_mission(pk)

            if (
                mission.status != BountyMission.Status.PENDING_VERIFICATION
                or mission.claimed_result not in BountyMission.ClaimedResult.values
            ):
                return Response(
                    {"detail": "Cette mission n'attend pas de vérification."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            mission_status_by_result = {
                BountyMission.ClaimedResult.CAPTURED: (
                    BountyMission.Status.CAPTURED
                ),
                BountyMission.ClaimedResult.KILLED: (
                    BountyMission.Status.KILLED
                ),
            }
            wanted_status_by_result = {
                BountyMission.ClaimedResult.CAPTURED: (
                    WantedPerson.Status.CAPTURED
                ),
                BountyMission.ClaimedResult.KILLED: (
                    WantedPerson.Status.DEAD
                ),
            }

            mission.received_by = request.user.sheriff_profile
            mission.received_at = timezone.now()
            mission.status = mission_status_by_result[mission.claimed_result]
            mission.save(
                update_fields=["received_by", "received_at", "status"]
            )

            mission.wanted_person.status = wanted_status_by_result[
                mission.claimed_result
            ]
            mission.wanted_person.save(update_fields=["status"])

            (
                BountyMission.objects.select_for_update()
                .filter(
                    wanted_person=mission.wanted_person,
                    status__in=[
                        BountyMission.Status.OPEN,
                        BountyMission.Status.PENDING_VERIFICATION,
                    ],
                )
                .exclude(pk=mission.pk)
                .update(status=BountyMission.Status.CANCELLED)
            )

        return Response(self.get_serializer(mission).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="reject-result",
    )
    def reject_result(self, request, pk=None):
        with transaction.atomic():
            mission = self._get_locked_mission(pk)

            if mission.status != BountyMission.Status.PENDING_VERIFICATION:
                return Response(
                    {"detail": "Cette mission n'attend pas de vérification."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            mission.hunter = None
            mission.claimed_result = None
            mission.claimed_at = None
            mission.status = BountyMission.Status.OPEN
            mission.save(
                update_fields=[
                    "hunter",
                    "claimed_result",
                    "claimed_at",
                    "status",
                ]
            )

        return Response(self.get_serializer(mission).data)


class HunterViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Hunter.objects.all()
    serializer_class = HunterSerializer
    permission_classes = [CanViewHunter]

    def get_queryset(self):
        return (
            Hunter.objects.prefetch_related("missions")
            .annotate(
                computed_balance=Sum(
                    "missions__reward",
                    filter=Q(
                        missions__status__in=[
                            BountyMission.Status.CAPTURED,
                            BountyMission.Status.KILLED,
                        ]
                    ),
                )
            )
        )

    @action(detail=False, methods=["get"])
    def me(self, request):
        hunter = self.get_queryset().get(pk=request.user.hunter_profile.pk)
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
