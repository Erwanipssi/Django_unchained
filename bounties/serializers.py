from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from .models import BountyMission, Hunter, Sheriff, User, WantedPerson


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
            "claimed_result",
            "claimed_at",
            "received_at",
            "status",
        ]
        read_only_fields = [
            "hunter",
            "commissioned_by",
            "received_by",
            "claimed_result",
            "claimed_at",
            "received_at",
            "status",
        ]


class HunterSerializer(serializers.ModelSerializer):
    missions = BountyMissionSerializer(many=True, read_only=True)
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Hunter
        fields = [
            "id",
            "nickname",
            "license_number",
            "balance",
            "missions",
        ]

    def get_balance(self, hunter):
        result = hunter.missions.filter(
            status__in=[
                BountyMission.Status.CAPTURED,
                BountyMission.Status.KILLED,
            ]
        ).aggregate(total=Sum("reward"))
        total = result["total"] or Decimal("0.00")
        return total.quantize(Decimal("0.01"))


class HunterRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    nickname = serializers.CharField(max_length=150)
    license_number = serializers.CharField(max_length=50)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur existe déjà.")
        return value

    def validate_license_number(self, value):
        if Hunter.objects.filter(license_number=value).exists():
            raise serializers.ValidationError("Ce numéro de licence existe déjà.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role=User.Role.HUNTER,
        )
        return Hunter.objects.create(
            user=user,
            nickname=validated_data["nickname"],
            license_number=validated_data["license_number"],
        )


class SheriffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sheriff
        fields = [
            "id",
            "mandate_started_at",
            "mandate_ended_at",
            "city",
        ]


class SheriffRegistrationSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    mandate_started_at = serializers.DateField()
    mandate_ended_at = serializers.DateField(required=False, allow_null=True)
    city = serializers.CharField(max_length=150)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Ce nom d'utilisateur existe déjà.")
        return value

    def validate(self, data):
        mandate_ended_at = data.get("mandate_ended_at")
        if mandate_ended_at and mandate_ended_at < data["mandate_started_at"]:
            raise serializers.ValidationError(
                "La fin du mandat ne peut pas précéder son début."
            )
        return data

    @transaction.atomic
    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
            role=User.Role.SHERIFF,
        )
        return Sheriff.objects.create(
            user=user,
            mandate_started_at=validated_data["mandate_started_at"],
            mandate_ended_at=validated_data.get("mandate_ended_at"),
            city=validated_data["city"],
        )
