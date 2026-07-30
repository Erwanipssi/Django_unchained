from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import BountyMission, Hunter, Sheriff, User, WantedPerson


class BountyApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.sheriff_user = User.objects.create_user(
            username="sheriff",
            password="A-strong-sheriff-password-2026",
            role=User.Role.SHERIFF,
        )
        self.sheriff = Sheriff.objects.create(
            user=self.sheriff_user,
            mandate_started_at=date(2026, 1, 1),
            city="Tombstone",
        )

        self.hunter_user = User.objects.create_user(
            username="hunter",
            password="A-strong-hunter-password-2026",
            role=User.Role.HUNTER,
        )
        self.hunter = Hunter.objects.create(
            user=self.hunter_user,
            nickname="Django",
            license_number="H-001",
        )

        self.wanted_person = WantedPerson.objects.create(
            name="Billy Crash",
            description="Recherché pour attaque de diligence.",
            danger_level=WantedPerson.DangerLevel.HIGH,
        )
        self.mission = BountyMission.objects.create(
            wanted_person=self.wanted_person,
            commissioned_by=self.sheriff,
            reward=Decimal("5000.00"),
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_wanted_person_status_cannot_be_changed_directly(self):
        self.authenticate(self.sheriff_user)

        response = self.client.patch(
            f"/api/wanted-persons/{self.wanted_person.pk}/",
            {"status": WantedPerson.Status.CAPTURED},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.wanted_person.refresh_from_db()
        self.assertEqual(
            self.wanted_person.status,
            WantedPerson.Status.WANTED,
        )

    def test_claim_uses_a_choice_serializer(self):
        self.authenticate(self.hunter_user)

        response = self.client.post(
            f"/api/missions/{self.mission.pk}/claim/",
            {"result": "ESCAPED"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("result", response.data)
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.status, BountyMission.Status.OPEN)

    def test_validating_a_claim_updates_target_and_cancels_other_missions(self):
        other_open_mission = BountyMission.objects.create(
            wanted_person=self.wanted_person,
            commissioned_by=self.sheriff,
            reward=Decimal("2500.00"),
        )
        other_pending_mission = BountyMission.objects.create(
            wanted_person=self.wanted_person,
            commissioned_by=self.sheriff,
            hunter=self.hunter,
            reward=Decimal("1000.00"),
            claimed_result=BountyMission.ClaimedResult.KILLED,
            status=BountyMission.Status.PENDING_VERIFICATION,
        )

        self.authenticate(self.hunter_user)
        claim_response = self.client.post(
            f"/api/missions/{self.mission.pk}/claim/",
            {"result": BountyMission.ClaimedResult.CAPTURED},
            format="json",
        )
        self.assertEqual(claim_response.status_code, status.HTTP_200_OK)

        self.authenticate(self.sheriff_user)
        validate_response = self.client.post(
            f"/api/missions/{self.mission.pk}/validate-result/",
            {},
            format="json",
        )
        self.assertEqual(validate_response.status_code, status.HTTP_200_OK)

        self.mission.refresh_from_db()
        self.wanted_person.refresh_from_db()
        other_open_mission.refresh_from_db()
        other_pending_mission.refresh_from_db()

        self.assertEqual(
            self.mission.status,
            BountyMission.Status.CAPTURED,
        )
        self.assertEqual(
            self.wanted_person.status,
            WantedPerson.Status.CAPTURED,
        )
        self.assertEqual(
            other_open_mission.status,
            BountyMission.Status.CANCELLED,
        )
        self.assertEqual(
            other_pending_mission.status,
            BountyMission.Status.CANCELLED,
        )

    def test_rejecting_a_claim_reopens_the_mission(self):
        self.mission.hunter = self.hunter
        self.mission.claimed_result = BountyMission.ClaimedResult.KILLED
        self.mission.status = BountyMission.Status.PENDING_VERIFICATION
        self.mission.save()
        self.authenticate(self.sheriff_user)

        response = self.client.post(
            f"/api/missions/{self.mission.pk}/reject-result/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.status, BountyMission.Status.OPEN)
        self.assertIsNone(self.mission.hunter)
        self.assertIsNone(self.mission.claimed_result)
        self.assertIsNone(self.mission.claimed_at)

    def test_validated_kill_marks_the_mission_killed_and_target_dead(self):
        self.mission.hunter = self.hunter
        self.mission.claimed_result = BountyMission.ClaimedResult.KILLED
        self.mission.status = BountyMission.Status.PENDING_VERIFICATION
        self.mission.save()
        self.authenticate(self.sheriff_user)

        response = self.client.post(
            f"/api/missions/{self.mission.pk}/validate-result/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mission.refresh_from_db()
        self.wanted_person.refresh_from_db()
        self.assertEqual(self.mission.status, BountyMission.Status.KILLED)
        self.assertEqual(
            self.wanted_person.status,
            WantedPerson.Status.DEAD,
        )

    def test_target_cannot_be_changed_after_mission_creation(self):
        other_target = WantedPerson.objects.create(
            name="Smitty Bacall",
            description="Recherché pour vol de chevaux.",
        )
        self.authenticate(self.sheriff_user)

        response = self.client.patch(
            f"/api/missions/{self.mission.pk}/",
            {"wanted_person": other_target.pk},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("wanted_person", response.data)

    def test_only_an_open_mission_can_be_modified(self):
        self.mission.status = BountyMission.Status.PENDING_VERIFICATION
        self.mission.save(update_fields=["status"])
        self.authenticate(self.sheriff_user)

        response = self.client.patch(
            f"/api/missions/{self.mission.pk}/",
            {"reward": "6000.00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mission.refresh_from_db()
        self.assertEqual(self.mission.reward, Decimal("5000.00"))

    def test_delete_cancels_an_open_mission_without_deleting_it(self):
        self.authenticate(self.sheriff_user)

        response = self.client.delete(
            f"/api/missions/{self.mission.pk}/",
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.mission.refresh_from_db()
        self.assertEqual(
            self.mission.status,
            BountyMission.Status.CANCELLED,
        )

    def test_delete_cannot_cancel_a_mission_in_progress(self):
        self.mission.status = BountyMission.Status.PENDING_VERIFICATION
        self.mission.save(update_fields=["status"])
        self.authenticate(self.sheriff_user)

        response = self.client.delete(
            f"/api/missions/{self.mission.pk}/",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.mission.refresh_from_db()
        self.assertEqual(
            self.mission.status,
            BountyMission.Status.PENDING_VERIFICATION,
        )

    def test_negative_reward_is_rejected(self):
        self.authenticate(self.sheriff_user)

        response = self.client.post(
            "/api/missions/",
            {
                "wanted_person": self.wanted_person.pk,
                "reward": "-1.00",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reward", response.data)

    def test_hunter_list_query_count_does_not_grow_per_hunter(self):
        second_user = User.objects.create_user(
            username="second-hunter",
            password="A-strong-second-password-2026",
            role=User.Role.HUNTER,
        )
        second_hunter = Hunter.objects.create(
            user=second_user,
            nickname="Second",
            license_number="H-002",
        )
        BountyMission.objects.create(
            wanted_person=self.wanted_person,
            commissioned_by=self.sheriff,
            hunter=second_hunter,
            reward=Decimal("300.00"),
            status=BountyMission.Status.CAPTURED,
        )

        with self.assertNumQueries(2):
            response = self.client.get("/api/hunters/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)


class ProfileConsistencyTestCase(TestCase):
    def test_profile_must_match_the_user_role(self):
        sheriff_user = User.objects.create_user(
            username="wrong-role",
            password="A-strong-password-2026",
            role=User.Role.SHERIFF,
        )

        with self.assertRaises(ValidationError):
            Hunter.objects.create(
                user=sheriff_user,
                nickname="Impossible",
                license_number="INVALID-001",
            )

    def test_user_cannot_have_both_profiles(self):
        user = User.objects.create_user(
            username="one-profile-only",
            password="A-strong-password-2026",
            role=User.Role.HUNTER,
        )
        Hunter.objects.create(
            user=user,
            nickname="Hunter",
            license_number="H-003",
        )

        User.objects.filter(pk=user.pk).update(role=User.Role.SHERIFF)
        user.refresh_from_db()

        with self.assertRaises(ValidationError):
            Sheriff.objects.create(
                user=user,
                mandate_started_at=date(2026, 1, 1),
                city="Tombstone",
            )

    def test_existing_profile_prevents_role_change(self):
        user = User.objects.create_user(
            username="fixed-role",
            password="A-strong-password-2026",
            role=User.Role.HUNTER,
        )
        Hunter.objects.create(
            user=user,
            nickname="Hunter",
            license_number="H-004",
        )

        user.role = User.Role.SHERIFF

        with self.assertRaises(ValidationError):
            user.save()


class RegistrationValidationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="admin",
            password="A-strong-admin-password-2026",
            role=User.Role.SHERIFF,
        )
        self.client.force_authenticate(user=self.admin)

    def test_weak_password_is_rejected(self):
        response = self.client.post(
            "/api/register/hunter/",
            {
                "username": "new-hunter",
                "password": "123",
                "first_name": "New",
                "last_name": "Hunter",
                "nickname": "Newbie",
                "license_number": "H-005",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username="new-hunter").exists())
