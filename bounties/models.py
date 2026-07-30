from decimal import Decimal

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        HUNTER = "HUNTER", "Chasseur de primes"
        SHERIFF = "SHERIFF", "Shérif"

    role = models.CharField(max_length=10, choices=Role.choices)

    REQUIRED_FIELDS = ["role"]

    def clean(self):
        super().clean()
        if not self.pk:
            return

        if (
            self.role != self.Role.HUNTER
            and hasattr(self, "hunter_profile")
        ):
            raise ValidationError(
                {
                    "role": (
                        "Un utilisateur avec un profil chasseur "
                        "doit garder le rôle HUNTER."
                    )
                }
            )
        if (
            self.role != self.Role.SHERIFF
            and hasattr(self, "sheriff_profile")
        ):
            raise ValidationError(
                {
                    "role": (
                        "Un utilisateur avec un profil shérif "
                        "doit garder le rôle SHERIFF."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

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

    def clean(self):
        super().clean()
        if not self.user_id:
            return

        if self.user.role != User.Role.HUNTER:
            raise ValidationError(
                {"user": "Le profil chasseur exige un utilisateur de rôle HUNTER."}
            )
        if hasattr(self.user, "sheriff_profile"):
            raise ValidationError(
                {"user": "Cet utilisateur possède déjà un profil shérif."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

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

    def clean(self):
        super().clean()
        if not self.user_id:
            return

        if self.user.role != User.Role.SHERIFF:
            raise ValidationError(
                {"user": "Le profil shérif exige un utilisateur de rôle SHERIFF."}
            )
        if hasattr(self.user, "hunter_profile"):
            raise ValidationError(
                {"user": "Cet utilisateur possède déjà un profil chasseur."}
            )

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

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
        CANCELLED = "CANCELLED", "Annulée"

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
    reward = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
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
