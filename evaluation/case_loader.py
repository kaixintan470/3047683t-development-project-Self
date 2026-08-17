"""Load synthetic evaluation cases without exposing evaluation labels to the pipeline."""

from dataclasses import fields
import json
from pathlib import Path
from typing import Any

from core.schemas import PatientState


DEFAULT_DATASET_PATH = Path("test_data/female_genitourinary_cases.json")
PATIENT_STATE_FIELDS = {field.name for field in fields(PatientState)}
EVALUATION_ONLY_FIELDS = {
    "target_category",
    "expected_information_state",
    "key_missing_information",
    "follow_up_reference",
    "expected_evidence_topics",
    "evaluation_note",
}


def load_case_dataset(path: str | Path = DEFAULT_DATASET_PATH) -> dict[str, Any]:
    """Load the deterministic synthetic dataset exactly as stored."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("cases"), list):
        raise ValueError("case dataset must contain a cases list")
    return payload


def select_case(
    case_id: str,
    dataset: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return one dataset record by its unique case identifier."""
    source = dataset if dataset is not None else load_case_dataset()
    matches = [case for case in source["cases"] if case.get("case_id") == case_id]
    if len(matches) != 1:
        raise KeyError(f"case_id must identify exactly one case: {case_id}")
    return matches[0]


def patient_state_from_case(case: dict[str, Any]) -> PatientState:
    """Convert only initial_patient_state into the production PatientState."""
    initial = case.get("initial_patient_state")
    if not isinstance(initial, dict):
        raise ValueError("case must contain an initial_patient_state object")
    unknown_fields = set(initial) - PATIENT_STATE_FIELDS
    if unknown_fields:
        raise ValueError(f"unknown PatientState fields: {sorted(unknown_fields)}")
    return PatientState(**initial)
