"""Django views for the concept-normalisation interaction prototype."""

from __future__ import annotations

import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from portal.concept_demo import rank_concepts
from portal.models import ConceptConfirmation, MedicalConcept


@login_required(login_url="login")
def concept_demo_home(request):
    return render(request, "portal/concept_demo.html")


@require_POST
@login_required(login_url="login")
def concept_match_api(request):
    try:
        payload = json.loads(request.body or "{}")
        patient_text = str(payload.get("patient_text", "")).strip()
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    if not patient_text:
        return JsonResponse({"error": "Please enter the patient's wording."}, status=400)

    return JsonResponse(
        {
            "patient_text": patient_text,
            "candidates": rank_concepts(patient_text, top_k=5),
        }
    )


@require_POST
@login_required(login_url="login")
def concept_confirm_api(request):
    try:
        payload = json.loads(request.body or "{}")
        patient_text = str(payload.get("patient_text", "")).strip()
        codes = payload.get("codes", [])
    except (json.JSONDecodeError, TypeError, ValueError):
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    if not patient_text:
        return JsonResponse({"error": "Patient text is required."}, status=400)
    if not isinstance(codes, list) or not all(isinstance(code, str) for code in codes):
        return JsonResponse({"error": "codes must be a list of strings."}, status=400)

    concepts = list(MedicalConcept.objects.filter(code__in=codes))
    by_code = {concept.code: concept for concept in concepts}
    selected = [
        {
            "code": code,
            "canonical_term": by_code[code].canonical_term,
            "display_label": by_code[code].display_label,
        }
        for code in codes
        if code in by_code
    ]

    record = ConceptConfirmation.objects.create(
        user=request.user,
        patient_text=patient_text,
        selected_concepts=selected,
    )
    return JsonResponse(
        {
            "status": "confirmed",
            "confirmation_id": record.id,
            "patient_text": patient_text,
            "selected_concepts": selected,
        }
    )
