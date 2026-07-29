from rest_framework import serializers

from .models import BountyMission, WantedPerson


class WantedPersonSerializer(serializers.ModelSerializer):
    class Meta:
        model = WantedPerson
        fields = [
            "id",
            "name",
            "description",
            "danger_level",
            "status",
        ]


class BountyMissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BountyMission
        fields = [
            "id",
            "wanted_person",
            "hunter",
            "commissioned_by",
            "received_by",
            "reward",
            "started_at",
            "completed_at",
            "received_at",
            "status",
        ]
