from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        HUNTER = "HUNTER", "Chasseur de primes"
        SHERIFF = "SHERIFF", "Shérif"

    role = models.CharField(max_length=10, choices=Role.choices)

    REQUIRED_FIELDS = ["role"]

    def __str__(self):
        return self.get_full_name() or self.username


class Hunter(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hunter_profile",
        limit_choices_to={"role": User.Role.HUNTER},
    )
    nickname = models.CharField(max_length=150)
    license_number = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.nickname


class Sheriff(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sheriff_profile",
        limit_choices_to={"role": User.Role.SHERIFF},
    )
    mandate_started_at = models.DateField()
    mandate_ended_at = models.DateField(null=True, blank=True)
    city = models.CharField(max_length=150)

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class WantedPerson(models.Model):
    class DangerLevel(models.TextChoices):
        LOW = "LOW", "Faible"
        MEDIUM = "MEDIUM", "Moyen"
        HIGH = "HIGH", "Élevé"

    class Status(models.TextChoices):
        WANTED = "WANTED", "Recherché"
        CAPTURED = "CAPTURED", "Capturé"
        DEAD = "DEAD", "Mort"

    name = models.CharField(max_length=150)
    description = models.TextField()
    danger_level = models.CharField(
        max_length=10,
        choices=DangerLevel.choices,
        default=DangerLevel.MEDIUM,
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.WANTED,
    )

    def __str__(self):
        return self.name


class BountyMission(models.Model):
    class Status(models.TextChoices):
        OPEN = "OPEN", "Disponible"
        PENDING_VERIFICATION = (
            "PENDING_VERIFICATION",
            "En attente de vérification",
        )
        CAPTURED = "CAPTURED", "Capture validée"
        KILLED = "KILLED", "Élimination validée"

    class ClaimedResult(models.TextChoices):
        CAPTURED = "CAPTURED", "Cible capturée"
        KILLED = "KILLED", "Cible éliminée"

    wanted_person = models.ForeignKey(
        WantedPerson,
        on_delete=models.PROTECT,
        related_name="missions",
    )
    hunter = models.ForeignKey(
        Hunter,
        on_delete=models.PROTECT,
        related_name="missions",
        null=True,
        blank=True,
    )
    commissioned_by = models.ForeignKey(
        Sheriff,
        on_delete=models.PROTECT,
        related_name="commissioned_missions",
    )
    received_by = models.ForeignKey(
        Sheriff,
        on_delete=models.PROTECT,
        related_name="received_missions",
        null=True,
        blank=True,
    )
    reward = models.DecimalField(max_digits=10, decimal_places=2)
    claimed_result = models.CharField(
        max_length=10,
        choices=ClaimedResult.choices,
        null=True,
        blank=True,
    )
    claimed_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
    )

    def __str__(self):
        return f"Mission contre {self.wanted_person}"
