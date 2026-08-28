"""Persistent patient-owned snapshots and concept-confirmation data."""

from django.conf import settings
from django.db import models


class AssessmentRecord(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assessment_records",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    decision = models.CharField(max_length=64)
    likely_condition = models.CharField(max_length=255, blank=True, default="")
    assessment_summary = models.TextField(blank=True, default="")
    kas = models.FloatField(null=True, blank=True)
    lcs = models.IntegerField(null=True, blank=True)
    dcs = models.FloatField(null=True, blank=True)
    patient_snapshot = models.JSONField(default=dict)
    result_snapshot = models.JSONField(default=dict)

    class Meta:
        ordering = ["-created_at"]


class MedicalConcept(models.Model):
    """Canonical CHV/UMLS concept used for patient confirmation."""

    code = models.CharField(max_length=64, unique=True)
    canonical_term = models.CharField(max_length=255)
    display_label = models.CharField(max_length=255)
    category = models.CharField(max_length=64, default="CHV")
    aliases = models.JSONField(default=list)

    class Meta:
        ordering = ["display_label"]

    def __str__(self) -> str:
        return f"{self.display_label} ({self.canonical_term})"


class MedicalTerm(models.Model):
    """One consumer/professional term mapped to a canonical CHV/UMLS concept."""

    concept = models.ForeignKey(
        MedicalConcept,
        on_delete=models.CASCADE,
        related_name="terms",
    )
    term = models.CharField(max_length=500)
    normalized_term = models.CharField(max_length=500, db_index=True)
    explanation = models.TextField(blank=True, default="")
    umls_preferred = models.BooleanField(default=False)
    chv_preferred = models.BooleanField(default=False)
    disparaged = models.BooleanField(default=False)
    frequency_score = models.FloatField(null=True, blank=True)
    context_score = models.FloatField(null=True, blank=True)
    cui_score = models.FloatField(null=True, blank=True)
    combo_score = models.FloatField(null=True, blank=True)
    combo_score_no_top_words = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["normalized_term", "disparaged"]),
        ]

    def __str__(self) -> str:
        return self.term


class ConceptConfirmation(models.Model):
    """Patient-confirmed mapping from lay text to controlled clinical concepts."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="concept_confirmations",
    )
    patient_text = models.TextField()
    selected_concepts = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
