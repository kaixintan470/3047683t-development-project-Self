"""Import the Open Consumer Health Vocabulary flat file into SQLite."""

from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from portal.models import MedicalConcept, MedicalTerm


COLUMNS = [
    "CUI",
    "Term",
    "CHV_preferred_name",
    "UMLS_preferred_name",
    "Explanation",
    "UMLS_preferred",
    "CHV_preferred",
    "Disparaged",
    "Frequency_Score",
    "Context_Score",
    "CUI_Score",
    "Combo_Score",
    "Combo_Score_NoTopWords",
    "CHV_String_Id",
    "CHV_Concept_Id",
]


def _bool(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def _float(value: str):
    value = str(value).strip()
    if not value:
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _normalise(text: str) -> str:
    return " ".join(str(text).strip().lower().split())


class Command(BaseCommand):
    help = "Import CHV_concepts_terms_flatfile_20110204.tsv into MedicalConcept/MedicalTerm."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Path to CHV_concepts_terms_flatfile_20110204.tsv")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete existing CHV concepts/terms before import.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        path = Path(options["path"])
        if not path.exists():
            raise CommandError(f"CHV file not found: {path}")

        if options["replace"]:
            MedicalTerm.objects.all().delete()
            MedicalConcept.objects.filter(category="CHV").delete()

        concept_cache: dict[str, MedicalConcept] = {}
        terms_to_create: list[MedicalTerm] = []
        imported_rows = 0

        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            reader = csv.DictReader(handle, fieldnames=COLUMNS, delimiter="\t")
            for row in reader:
                cui = (row.get("CUI") or "").strip()
                term = (row.get("Term") or "").strip()
                if not cui or not term:
                    continue

                concept = concept_cache.get(cui)
                if concept is None:
                    preferred = (
                        (row.get("CHV_preferred_name") or "").strip()
                        or (row.get("UMLS_preferred_name") or "").strip()
                        or term
                    )
                    concept, _ = MedicalConcept.objects.update_or_create(
                        code=cui,
                        defaults={
                            "canonical_term": (row.get("UMLS_preferred_name") or "").strip() or preferred,
                            "display_label": preferred,
                            "category": "CHV",
                            "aliases": [],
                        },
                    )
                    concept_cache[cui] = concept

                terms_to_create.append(
                    MedicalTerm(
                        concept=concept,
                        term=term,
                        normalized_term=_normalise(term),
                        explanation=(row.get("Explanation") or "").strip(),
                        umls_preferred=_bool(row.get("UMLS_preferred") or ""),
                        chv_preferred=_bool(row.get("CHV_preferred") or ""),
                        disparaged=_bool(row.get("Disparaged") or ""),
                        frequency_score=_float(row.get("Frequency_Score") or ""),
                        context_score=_float(row.get("Context_Score") or ""),
                        cui_score=_float(row.get("CUI_Score") or ""),
                        combo_score=_float(row.get("Combo_Score") or ""),
                        combo_score_no_top_words=_float(row.get("Combo_Score_NoTopWords") or ""),
                    )
                )
                imported_rows += 1

                if len(terms_to_create) >= 5000:
                    MedicalTerm.objects.bulk_create(terms_to_create, batch_size=1000)
                    terms_to_create.clear()

        if terms_to_create:
            MedicalTerm.objects.bulk_create(terms_to_create, batch_size=1000)

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {imported_rows} CHV term rows across {len(concept_cache)} concepts."
            )
        )
