"""State data and transitions for the fixed interview + concept mapping flow."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, TypedDict

from core.interview import (
    INTERVIEW_FIELDS,
    INTERVIEW_QUESTIONS,
    NEGATIVE_ANSWERS,
    update_patient_field,
)
from core.schemas import PatientState
from portal.concept_demo import rank_concepts


# For the first working version, only the two free-text symptom fields enter
# concept confirmation. The remaining fixed questions are stored directly.
MAPPING_FIELDS = {
    "chief_complaint",
    "symptoms",
}


class HistoryItem(TypedDict):
    field: str
    question: str
    answer: str
    concepts: list[dict[str, Any]]


class ConflictState(TypedDict):
    field: str
    question: str
    answer: str
    candidates: list[dict[str, Any]]


class ViewState(TypedDict):
    stage: str
    question_index: int
    current_field: str | None
    current_question: str | None
    patient: dict[str, Any]
    history: list[HistoryItem]
    conflict: ConflictState | None
    complete: bool


def initial_view_state() -> ViewState:
    first_field = INTERVIEW_FIELDS[0]
    return {
        "stage": "INTERVIEW",
        "question_index": 0,
        "current_field": first_field,
        "current_question": INTERVIEW_QUESTIONS[first_field],
        "patient": asdict(PatientState()),
        "history": [],
        "conflict": None,
        "complete": False,
    }


def _commit_patient_answer(state: ViewState, field_name: str, answer: str) -> None:
    """Update the same PatientState structure used by the original clinical pipeline."""
    patient = PatientState(**state.get("patient", {}))
    update_patient_field(patient, field_name, answer)
    state["patient"] = asdict(patient)


def _advance(state: ViewState) -> ViewState:
    next_index = state["question_index"] + 1
    state["question_index"] = next_index
    state["conflict"] = None

    if next_index >= len(INTERVIEW_FIELDS):
        state["stage"] = "COMPLETE"
        state["current_field"] = None
        state["current_question"] = None
        state["complete"] = True
        return state

    next_field = INTERVIEW_FIELDS[next_index]
    state["stage"] = "INTERVIEW"
    state["current_field"] = next_field
    state["current_question"] = INTERVIEW_QUESTIONS[next_field]
    return state


def submit_answer(state: ViewState, answer: str) -> ViewState:
    """Handle one answer; symptom text pauses in CONFLICT until mapping is confirmed."""
    if state["complete"]:
        raise ValueError("The interview is already complete.")
    if state["conflict"] is not None:
        raise ValueError("Resolve the current concept conflict before answering the next question.")

    cleaned = answer.strip()
    if not cleaned:
        raise ValueError("Answer cannot be empty.")

    field = state["current_field"]
    question = state["current_question"]
    if field is None or question is None:
        raise ValueError("No active interview question.")

    should_map = field in MAPPING_FIELDS and cleaned.casefold() not in NEGATIVE_ANSWERS
    if should_map:
        candidates = rank_concepts(cleaned, top_k=5)
        state["stage"] = "CONFLICT"
        state["conflict"] = {
            "field": field,
            "question": question,
            "answer": cleaned,
            "candidates": candidates,
        }
        return state

    _commit_patient_answer(state, field, cleaned)
    state["history"].append(
        {
            "field": field,
            "question": question,
            "answer": cleaned,
            "concepts": [],
        }
    )
    return _advance(state)


def confirm_conflict(state: ViewState, codes: list[str]) -> ViewState:
    """Confirm one or more of the Top-K concepts, then commit the original answer."""
    conflict = state["conflict"]
    if conflict is None:
        raise ValueError("There is no concept conflict to confirm.")
    if not codes:
        raise ValueError("Select at least one concept or choose 'none of these'.")

    candidate_by_code = {
        str(candidate["code"]): candidate for candidate in conflict["candidates"]
    }
    invalid = [code for code in codes if code not in candidate_by_code]
    if invalid:
        raise ValueError("A selected concept was not part of the presented candidates.")

    selected = [candidate_by_code[code] for code in codes]
    _commit_patient_answer(state, conflict["field"], conflict["answer"])
    state["history"].append(
        {
            "field": conflict["field"],
            "question": conflict["question"],
            "answer": conflict["answer"],
            "concepts": selected,
        }
    )
    return _advance(state)


def reject_conflict(state: ViewState) -> ViewState:
    """Clear candidate mapping and stay on the same fixed question for re-wording."""
    if state["conflict"] is None:
        raise ValueError("There is no concept conflict to reject.")
    state["conflict"] = None
    state["stage"] = "INTERVIEW"
    return state
