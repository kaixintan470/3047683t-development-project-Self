# Generated for the concept-normalisation UI prototype.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MedicalConcept",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64, unique=True)),
                ("canonical_term", models.CharField(max_length=255)),
                ("display_label", models.CharField(max_length=255)),
                ("category", models.CharField(default="symptom", max_length=64)),
                ("aliases", models.JSONField(default=list)),
            ],
            options={"ordering": ["display_label"]},
        ),
        migrations.CreateModel(
            name="ConceptConfirmation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("patient_text", models.TextField()),
                ("selected_concepts", models.JSONField(default=list)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="concept_confirmations",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
