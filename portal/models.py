"""Persistent patient-owned snapshots of completed real assessments."""

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
