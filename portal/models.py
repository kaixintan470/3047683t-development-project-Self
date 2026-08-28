"""Persistent patient-owned snapshots and concept-confirmation demo data."""

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
    """Small controlled vocabulary used by the concept-normalisation UI demo."""

    code = models.CharField(max_length=64, unique=True)
    canonical_term = models.CharField(max_length=255)
    display_label = models.CharField(max_length=255)
    category = models.CharField(max_length=64, default="symptom")
    aliases = models.JSONField(default=list)

    class Meta:
        ordering = ["display_label"]

    def __str__(self) -> str:
        return f"{self.display_label} ({self.canonical_term})"


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
