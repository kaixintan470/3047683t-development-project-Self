# Generated for full CHV/UMLS concept-term import support.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portal", "0002_medicalconcept_conceptconfirmation"),
    ]

    operations = [
        migrations.CreateModel(
            name="MedicalTerm",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("term", models.CharField(max_length=500)),
                ("normalized_term", models.CharField(db_index=True, max_length=500)),
                ("explanation", models.TextField(blank=True, default="")),
                ("umls_preferred", models.BooleanField(default=False)),
                ("chv_preferred", models.BooleanField(default=False)),
                ("disparaged", models.BooleanField(default=False)),
                ("frequency_score", models.FloatField(blank=True, null=True)),
                ("context_score", models.FloatField(blank=True, null=True)),
                ("cui_score", models.FloatField(blank=True, null=True)),
                ("combo_score", models.FloatField(blank=True, null=True)),
                ("combo_score_no_top_words", models.FloatField(blank=True, null=True)),
                (
                    "concept",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="terms",
                        to="portal.medicalconcept",
                    ),
                ),
            ],
        ),
        migrations.AddIndex(
            model_name="medicalterm",
            index=models.Index(fields=["normalized_term", "disparaged"], name="portal_medi_normali_742951_idx"),
        ),
    ]
