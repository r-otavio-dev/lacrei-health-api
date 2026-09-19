from __future__ import annotations

from rest_framework import status

from apps.scheduling.models import Professional
from apps.scheduling.tests.base import AuthenticatedAPITestCase


class ProfessionalCRUDTests(AuthenticatedAPITestCase):
    endpoint = "/api/v1/professionals/"

    def test_create_professional_sanitizes_whitespace(self) -> None:
        payload = self.professional_payload(
            social_name="  Alex   Silva  ",
            address="  Rua do\nAcolhimento, 100  ",
        )

        response = self.client.post(self.endpoint, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["social_name"], "Alex Silva")
        self.assertEqual(response.data["address"], "Rua do Acolhimento, 100")
        self.assertTrue(Professional.objects.filter(pk=response.data["id"]).exists())

    def test_list_and_retrieve_professionals(self) -> None:
        professional = self.create_professional()

        list_response = self.client.get(self.endpoint)
        detail_response = self.client.get(f"{self.endpoint}{professional.pk}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["results"][0]["id"], str(professional.pk))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["social_name"], professional.social_name)
        self.assertEqual(str(professional), "Alex Silva (Cardiologia)")

    def test_replace_professional(self) -> None:
        professional = self.create_professional()
        payload = self.professional_payload(
            social_name="Sam Oliveira",
            profession="Clínica Geral",
            contact="(11) 99999-0000",
        )

        response = self.client.put(
            f"{self.endpoint}{professional.pk}/",
            payload,
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        professional.refresh_from_db()
        self.assertEqual(professional.social_name, "Sam Oliveira")
        self.assertEqual(professional.profession, "Clínica Geral")

    def test_partially_update_professional(self) -> None:
        professional = self.create_professional()

        response = self.client.patch(
            f"{self.endpoint}{professional.pk}/",
            {"contact": "novo@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        professional.refresh_from_db()
        self.assertEqual(professional.contact, "novo@example.com")

    def test_delete_professional_without_appointments(self) -> None:
        professional = self.create_professional()

        response = self.client.delete(f"{self.endpoint}{professional.pk}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Professional.objects.filter(pk=professional.pk).exists())

    def test_delete_professional_with_appointment_returns_conflict(self) -> None:
        professional = self.create_professional()
        self.create_appointment(professional)

        response = self.client.delete(f"{self.endpoint}{professional.pk}/")

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data["error"]["code"], "professional_has_appointments")
        self.assertEqual(response.data["error"]["details"]["appointments"], 1)
        self.assertTrue(Professional.objects.filter(pk=professional.pk).exists())


class ProfessionalValidationTests(AuthenticatedAPITestCase):
    endpoint = "/api/v1/professionals/"

    def test_missing_required_fields_returns_json_validation_error(self) -> None:
        response = self.client.post(
            self.endpoint,
            {"social_name": "Alex"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.data["error"]["code"], "invalid")
        self.assertIn("profession", response.data["error"]["details"])

    def test_html_input_is_rejected(self) -> None:
        response = self.client.post(
            self.endpoint,
            self.professional_payload(social_name="<script>alert(1)</script>"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("social_name", response.data["error"]["details"])
        self.assertEqual(Professional.objects.count(), 0)

    def test_control_characters_are_rejected(self) -> None:
        response = self.client.post(
            self.endpoint,
            self.professional_payload(address="Rua segura\u0000, 10"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("address", response.data["error"]["details"])

    def test_field_too_short_after_normalization_is_rejected(self) -> None:
        response = self.client.post(
            self.endpoint,
            self.professional_payload(social_name=" A "),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("social_name", response.data["error"]["details"])

    def test_invalid_contact_characters_are_rejected(self) -> None:
        response = self.client.post(
            self.endpoint,
            self.professional_payload(contact="alex@example.com; delete"),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("contact", response.data["error"]["details"])

    def test_unauthenticated_request_is_rejected(self) -> None:
        self.client.force_authenticate(user=None)

        response = self.client.get(self.endpoint)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertEqual(response.data["error"]["code"], "not_authenticated")
