"""Neutral follow-up generation and bounded callback coordination."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from core.config import DEFAULT_CONFIG
from core.interview import INTERVIEW_FIELDS, NEGATIVE_ANSWERS, update_patient_field
from core.schemas import PatientState, SufficiencyResult


FollowupModelCall = Callable[[str], str | list[str]]


class FollowupStatus(str, Enum):
    PROCEED_TO_VALIDATION = "PROCEED_TO_VALIDATION"
    UNRESOLVED_INSUFFICIENT_INFORMATION = "UNRESOLVED_INSUFFICIENT_INFORMATION"


@dataclass
class FollowupLoopResult:
    status: FollowupStatus
    patient: PatientState
    follow_up_rounds: int


def merge_missing_information(
    slm_a_missing: list[str],
    slm_b_missing: list[str],
) -> list[str]:
    return list(dict.fromkeys(slm_a_missing + slm_b_missing))


def generate_followup_questions(
    missing_information: list[str],
    model_call: FollowupModelCall,
) -> list[str]:
    prompt = (
        "Using only the missing information below, write 1 or 2 short, neutral, "
        "patient-facing questions. Do not reveal or mention any diagnosis, model "
        "disagreement, or reasoning chain. Return one question per line.\n\n"
        + "\n".join(missing_information)
    )
    response = model_call(prompt)
    raw_questions = response if isinstance(response, list) else response.splitlines()
    questions = [question.strip() for question in raw_questions if question.strip()]
    if not questions:
        raise ValueError("follow-up generation must return at least 1 question")
    return questions[:2]


def apply_followup_answer(
    patient: PatientState,
    field_name: str,
    answer: str,
) -> PatientState:
    if field_name in INTERVIEW_FIELDS:
        return update_patient_field(patient, field_name, answer)

    cleaned_answer = answer.strip()
    patient.follow_up_answers[field_name] = cleaned_answer
    if cleaned_answer.casefold() in NEGATIVE_ANSWERS:
        if field_name not in patient.explicit_negations:
            patient.explicit_negations.append(field_name)
    elif field_name in patient.explicit_negations:
        patient.explicit_negations.remove(field_name)
    return patient


def run_followup_loop(
    patient: PatientState,
    slm_a_sufficiency: SufficiencyResult,
    slm_b_sufficiency: SufficiencyResult,
    query_retrieval: Callable[[PatientState], object],
    slm_a: Callable[[PatientState, object], object],
    slm_b: Callable[[PatientState, object], object],
    sufficiency_controller: Callable[
        [PatientState, object, object, object],
        tuple[SufficiencyResult, SufficiencyResult],
    ],
    question_generator: Callable[[list[str]], list[str]],
    answer_provider: Callable[[str], str],
) -> FollowupLoopResult:
    rounds = 0
    current_a = slm_a_sufficiency
    current_b = slm_b_sufficiency

    while rounds < DEFAULT_CONFIG.max_followup_rounds:
        if current_a.is_sufficient and current_b.is_sufficient:
            return FollowupLoopResult(
                FollowupStatus.PROCEED_TO_VALIDATION, patient, rounds
            )

        missing = merge_missing_information(
            current_a.missing_information,
            current_b.missing_information,
        )
        questions = question_generator(missing)
        if not questions or not missing:
            break

        for index, question in enumerate(questions):
            field_name = missing[min(index, len(missing) - 1)]
            apply_followup_answer(patient, field_name, answer_provider(question))

        rounds += 1
        evidence = query_retrieval(patient)
        result_a = slm_a(patient, evidence)
        result_b = slm_b(patient, evidence)
        current_a, current_b = sufficiency_controller(
            patient, evidence, result_a, result_b
        )

    return FollowupLoopResult(
        FollowupStatus.UNRESOLVED_INSUFFICIENT_INFORMATION,
        patient,
        rounds,
    )
