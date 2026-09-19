from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.scheduling.models import Appointment, Professional


class AuthenticatedAPITestCase(APITestCase):
    password = "a-strong-test-password-123"

    @classmethod
    def setUpTestData(cls) -> None:
        cls.user = get_user_model().objects.create_user(
            username="api-tester",
            email="api-tester@example.com",
            password=cls.password,
        )

    def setUp(self) -> None:
        self.client.force_authenticate(self.user)

    @staticmethod
    def professional_payload(**overrides: str) -> dict[str, str]:
        payload = {
            "social_name": "Alex Silva",
            "profession": "Cardiologia",
            "address": "Rua do Acolhimento, 100",
            "contact": "alex@example.com",
        }
        payload.update(overrides)
        return payload

    @classmethod
    def create_professional(cls, **overrides: str) -> Professional:
        payload = cls.professional_payload(**overrides)
        return Professional.objects.create(**payload)

    @staticmethod
    def future_date(days: int = 2):
        return timezone.now() + timedelta(days=days)

    @classmethod
    def create_appointment(
        cls,
        professional: Professional,
        *,
        days: int = 2,
    ) -> Appointment:
        return Appointment.objects.create(
            professional=professional,
            date=cls.future_date(days),
        )
