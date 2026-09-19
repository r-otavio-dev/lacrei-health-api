from __future__ import annotations

import re
import unicodedata

from django.utils import timezone
from django.utils.html import strip_tags
from rest_framework import serializers

from .models import Appointment, Professional

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
CONTACT_RE = re.compile(r"^[\w.!#$%&'*+/=?^`{|}~@()\-+\s]+$", re.UNICODE)


def clean_text(value: str, *, min_length: int) -> str:
    """Normalize user text and reject markup/control characters."""
    normalized = unicodedata.normalize("NFKC", value).strip()
    if CONTROL_CHARS.search(normalized):
        raise serializers.ValidationError("Caracteres de controle não são permitidos.")
    if "<" in normalized or ">" in normalized or strip_tags(normalized) != normalized:
        raise serializers.ValidationError("Tags HTML não são permitidas.")
    normalized = re.sub(r"\s+", " ", normalized)
    if len(normalized) < min_length:
        raise serializers.ValidationError(
            f"Este campo deve conter pelo menos {min_length} caracteres."
        )
    return normalized


class ProfessionalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Professional
        fields = (
            "id",
            "social_name",
            "profession",
            "address",
            "contact",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_social_name(self, value: str) -> str:
        return clean_text(value, min_length=2)

    def validate_profession(self, value: str) -> str:
        return clean_text(value, min_length=2)

    def validate_address(self, value: str) -> str:
        return clean_text(value, min_length=5)

    def validate_contact(self, value: str) -> str:
        value = clean_text(value, min_length=5)
        if not CONTACT_RE.fullmatch(value):
            raise serializers.ValidationError("Informe um e-mail ou telefone válido.")
        return value


class AppointmentSerializer(serializers.ModelSerializer):
    professional_name = serializers.CharField(source="professional.social_name", read_only=True)

    class Meta:
        model = Appointment
        fields = (
            "id",
            "date",
            "professional",
            "professional_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "professional_name", "created_at", "updated_at")
        validators = []

    def validate_date(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("A data da consulta deve estar no futuro.")
        return value

    def validate(self, attrs):
        professional = attrs.get("professional", getattr(self.instance, "professional", None))
        date = attrs.get("date", getattr(self.instance, "date", None))
        if professional and date:
            duplicate = Appointment.objects.filter(professional=professional, date=date)
            if self.instance:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise serializers.ValidationError(
                    {"date": "Esse profissional já possui uma consulta nesse horário."}
                )
        return attrs
