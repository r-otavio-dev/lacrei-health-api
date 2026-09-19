from __future__ import annotations

from datetime import timedelta

from django.utils import timezone
from rest_framework import status

from apps.scheduling.models import Appointment
from apps.scheduling.tests.base import AuthenticatedAPITestCase


class AppointmentCRUDTests(AuthenticatedAPITestCase):
    endpoint = "/api/v1/appointments/"

    def setUp(self) -> None:
        super().setUp()
        self.professional = self.create_professional()

    def test_create_appointment(self) -> None:
        date = self.future_date()

        response = self.client.post(
            self.endpoint,
            {"date": date.isoformat(), "professional": str(self.professional.pk)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(str(response.data["professional"]), str(self.professional.pk))
        self.assertEqual(response.data["professional_name"], self.professional.social_name)
        self.assertTrue(Appointment.objects.filter(pk=response.data["id"]).exists())

    def test_list_and_retrieve_appointments(self) -> None:
        appointment = self.create_appointment(self.professional)

        list_response = self.client.get(self.endpoint)
        detail_response = self.client.get(f"{self.endpoint}{appointment.pk}/")

        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data["count"], 1)
        self.assertEqual(list_response.data["results"][0]["id"], str(appointment.pk))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(detail_response.data["id"], str(appointment.pk))
        self.assertIn(self.professional.social_name, str(appointment))

    def test_replace_appointment(self) -> None:
        appointment = self.create_appointment(self.professional)
        replacement_professional = self.create_professional(
            social_name="Jordan Costa",
            contact="jordan@example.com",
        )
        replacement_date = self.future_date(7)

        response = self.client.put(
            f"{self.endpoint}{appointment.pk}/",
            {
                "date": replacement_date.isoformat(),
                "professional": str(replacement_professional.pk),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appointment.refresh_from_db()
        self.assertEqual(appointment.professional, replacement_professional)

    def test_partially_update_appointment(self) -> None:
        appointment = self.create_appointment(self.professional)
        replacement_date = self.future_date(10)

        response = self.client.patch(
            f"{self.endpoint}{appointment.pk}/",
            {"date": replacement_date.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appointment.refresh_from_db()
        self.assertAlmostEqual(
            appointment.date.timestamp(),
            replacement_date.timestamp(),
            delta=0.001,
        )

    def test_delete_appointment(self) -> None:
        appointment = self.create_appointment(self.professional)

        response = self.client.delete(f"{self.endpoint}{appointment.pk}/")

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Appointment.objects.filter(pk=appointment.pk).exists())


class AppointmentFilteringTests(AuthenticatedAPITestCase):
    endpoint = "/api/v1/appointments/"

    def setUp(self) -> None:
        super().setUp()
        self.professional = self.create_professional()
        self.other_professional = self.create_professional(
            social_name="Taylor Santos",
            contact="taylor@example.com",
        )
        self.appointment = self.create_appointment(self.professional)
        self.create_appointment(self.other_professional, days=3)

    def test_filter_by_professional_id(self) -> None:
        response = self.client.get(
            self.endpoint,
            {"professional_id": str(self.professional.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.appointment.pk))

    def test_filter_by_professional_alias(self) -> None:
        response = self.client.get(
            self.endpoint,
            {"professional": str(self.professional.pk)},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)

    def test_nested_professional_appointments_endpoint(self) -> None:
        response = self.client.get(f"/api/v1/professionals/{self.professional.pk}/appointments/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], str(self.appointment.pk))

    def test_invalid_professional_filter_rejects_sql_injection_string(self) -> None:
        response = self.client.get(
            self.endpoint,
            {"professional_id": "' OR 1=1; DROP TABLE appointments; --"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Appointment.objects.count(), 2)
        self.assertIn("professional", response.data["error"]["details"])


class AppointmentValidationTests(AuthenticatedAPITestCase):
    endpoint = "/api/v1/appointments/"

    def setUp(self) -> None:
        super().setUp()
        self.professional = self.create_professional()

    def test_past_date_is_rejected(self) -> None:
        response = self.client.post(
            self.endpoint,
            {
                "date": (timezone.now() - timedelta(minutes=1)).isoformat(),
                "professional": str(self.professional.pk),
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data["error"]["details"])

    def test_missing_fields_are_rejected(self) -> None:
        response = self.client.post(self.endpoint, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date", response.data["error"]["details"])
        self.assertIn("professional", response.data["error"]["details"])

    def test_unknown_professional_is_rejected(self) -> None:
        response = self.client.post(
            self.endpoint,
            {
                "date": self.future_date().isoformat(),
                "professional": "00000000-0000-0000-0000-000000000000",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("professional", response.data["error"]["details"])

    def test_duplicate_professional_datetime_is_rejected(self) -> None:
        date = self.future_date()
        Appointment.objects.create(professional=self.professional, date=date)

        response = self.client.post(
            self.endpoint,
            {"date": date.isoformat(), "professional": str(self.professional.pk)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertIn("date", response.data["error"]["details"])

    def test_update_to_duplicate_professional_datetime_is_rejected(self) -> None:
        occupied_date = self.future_date(5)
        Appointment.objects.create(professional=self.professional, date=occupied_date)
        appointment = self.create_appointment(self.professional, days=7)

        response = self.client.patch(
            f"{self.endpoint}{appointment.pk}/",
            {"date": occupied_date.isoformat()},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        appointment.refresh_from_db()
        self.assertNotEqual(appointment.date, occupied_date)
