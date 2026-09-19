from __future__ import annotations

import uuid

from django.core.validators import MinLengthValidator
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Professional(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    social_name = models.CharField(max_length=150, validators=[MinLengthValidator(2)])
    profession = models.CharField(max_length=100, validators=[MinLengthValidator(2)])
    address = models.CharField(max_length=255, validators=[MinLengthValidator(5)])
    contact = models.CharField(max_length=150, validators=[MinLengthValidator(5)])

    class Meta:
        ordering = ("social_name", "id")
        indexes = [models.Index(fields=("social_name",)), models.Index(fields=("profession",))]

    def __str__(self) -> str:
        return f"{self.social_name} ({self.profession})"


class Appointment(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    date = models.DateTimeField(db_index=True)
    professional = models.ForeignKey(
        Professional,
        on_delete=models.PROTECT,
        related_name="appointments",
    )

    class Meta:
        ordering = ("date", "id")
        constraints = [
            models.UniqueConstraint(
                fields=("professional", "date"),
                name="unique_professional_appointment_datetime",
            )
        ]
        indexes = [models.Index(fields=("professional", "date"))]

    def __str__(self) -> str:
        return f"{self.professional} - {self.date.isoformat()}"
