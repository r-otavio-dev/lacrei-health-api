# Generated manually to keep the initial schema deterministic.
import uuid

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Professional",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("social_name", models.CharField(max_length=150, validators=[django.core.validators.MinLengthValidator(2)])),
                ("profession", models.CharField(max_length=100, validators=[django.core.validators.MinLengthValidator(2)])),
                ("address", models.CharField(max_length=255, validators=[django.core.validators.MinLengthValidator(5)])),
                ("contact", models.CharField(max_length=150, validators=[django.core.validators.MinLengthValidator(5)])),
            ],
            options={"ordering": ("social_name", "id")},
        ),
        migrations.CreateModel(
            name="Appointment",
            fields=[
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("date", models.DateTimeField(db_index=True)),
                (
                    "professional",
                    models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="scheduling.professional"),
                ),
            ],
            options={
                "ordering": ("date", "id"),
                "constraints": [models.UniqueConstraint(fields=("professional", "date"), name="unique_professional_appointment_datetime")],
            },
        ),
        migrations.AddIndex(
            model_name="professional",
            index=models.Index(fields=["social_name"], name="scheduling__social__ff3771_idx"),
        ),
        migrations.AddIndex(
            model_name="professional",
            index=models.Index(fields=["profession"], name="scheduling__profess_07a752_idx"),
        ),
        migrations.AddIndex(
            model_name="appointment",
            index=models.Index(fields=["professional", "date"], name="scheduling__profess_225d3f_idx"),
        ),
    ]
