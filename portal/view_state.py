"""Lightweight state-machine logic for the /view interview mapping prototype."""

from __future__ import annotations

from typing import Any, TypedDict

from core.interview import INTERVIEW_FIELDS, INTERVIEW_QUESTIONS, NEGATIVE_ANSWERS
from portal.concept_demo import rank_concepts


MAPPING_FIELDS = {
    "chief_complaint",
    "symptoms",
    "medical_history",
    "allergies",
    "medications",
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
        "history": [],
        "conflict": None,
        "complete": False,
    }


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
    """Store a fixed-question answer or pause in CONFLICT for concept confirmation."""
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
    """Resolve the current mapping conflict using only candidates shown to the patient."""
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
    """Clear the conflict and keep the same fixed question for re-wording."""
    if state["conflict"] is None:
        raise ValueError("There is no concept conflict to reject.")
    state["conflict"] = None
    state["stage"] = "INTERVIEW"
    return state
