"""Per-model binary sufficiency evaluation and dual-AND routing."""

from collections.abc import Callable
from dataclasses import asdict
from enum import Enum
import json

from core.interview import INTERVIEW_FIELDS, NEGATIVE_ANSWERS
from core.reasoning import ReasoningResult
from core.schemas import EvidenceChunk, PatientState, SufficiencyResult


SufficiencyModelCall = Callable[[str], str]
RESPONSE_KEYS = {
    "patient_fact_support",
    "relevant_evidence_available",
    "no_critical_missing_discriminator",
    "no_unsupported_assumption",
    "rationale",
    "missing_information",
}


class SufficiencyRoute(str, Enum):
    FOLLOW_UP = "FOLLOW_UP"
    PROCEED_TO_VALIDATION = "PROCEED_TO_VALIDATION"


def _patient_information_state(patient: PatientState) -> str:
    present: list[str] = []
    absent: list[str] = []
    unknown: list[str] = []

    for field_name in INTERVIEW_FIELDS:
        value = getattr(patient, field_name)
        if value or value == 0:
            rendered = ", ".join(value) if isinstance(value, list) else str(value)
            present.append(f"{field_name}: {rendered}")
        elif field_name in patient.explicit_negations:
            absent.append(f"{field_name}: confirmed absent")
        else:
            unknown.append(field_name)

    for field_name, answer in patient.follow_up_answers.items():
        rendered = answer.strip()
        if rendered.casefold() in NEGATIVE_ANSWERS:
            absent.append(f"{field_name}: {rendered}")
        elif rendered:
            present.append(f"{field_name}: {rendered}")

    return (
        "CONFIRMED PRESENT\n"
        + ("\n".join(present) or "None")
        + "\n\nCONFIRMED ABSENT\n"
        + ("\n".join(absent) or "None")
        + "\n\nUNKNOWN / NOT YET PROVIDED\n"
        + ("\n".join(unknown) or "None")
    )


def build_sufficiency_prompt(
    patient: PatientState,
    evidence: list[EvidenceChunk],
    reasoning: ReasoningResult,
) -> str:
    return (
        "Evaluate only this model's result against exactly four binary "
        "prerequisites. Confirmed absence is known information, not missing "
        "information. A previously answered follow-up fact is known information. "
        "Do not mark a known fact as missing merely because the reasoning summary "
        "does not repeat it.\n\n"
        "C1 patient_fact_support: The reasoning is supported by known patient facts.\n"
        "C2 relevant_evidence_available: Relevant retrieved clinical evidence is "
        "available for the actual reasoning or candidate conclusion. Evidence is "
        "not required for excluded alternatives or confirmed-absent risk factors.\n"
        "C3 no_critical_missing_discriminator: TRUE means no critical diagnostic "
        "discriminator remains unknown. FALSE means at least one critical diagnostic "
        "discriminator remains unknown. C3 concerns only diagnostic discrimination; "
        "it must not request treatment plans, management plans, or facts already "
        "confirmed or denied.\n"
        "C4 no_unsupported_assumption: The reasoning does not depend on an "
        "unconfirmed patient fact. C4 concerns unsupported assumptions about this "
        "patient, not missing evidence for already excluded alternatives.\n\n"
        "Return only this exact JSON shape with booleans, a short rationale, and "
        "concrete unknown diagnostic discriminators only:\n"
        '{"patient_fact_support": true, "relevant_evidence_available": true, '
        '"no_critical_missing_discriminator": true, '
        '"no_unsupported_assumption": true, "rationale": "short rationale", '
        '"missing_information": []}\n'
        "Consistency is mandatory: when no_critical_missing_discriminator is true, "
        "missing_information must be empty; when it is false, missing_information "
        "must contain at least one concrete diagnostic discriminator. Do not expose "
        "chain-of-thought.\n\n"
        f"PATIENT INFORMATION STATE\n{_patient_information_state(patient)}\n\n"
        f"PATIENT JSON\n{json.dumps(asdict(patient), sort_keys=True)}\n\n"
        f"EVIDENCE\n{json.dumps([asdict(chunk) for chunk in evidence], sort_keys=True)}\n\n"
        f"THIS MODEL'S REASONING\n{json.dumps(asdict(reasoning), sort_keys=True)}"
    )


def _parse_sufficiency_response(response: str) -> SufficiencyResult:
    payload = json.loads(response)
    if not isinstance(payload, dict) or set(payload) != RESPONSE_KEYS:
        raise ValueError("sufficiency response must contain exactly the required keys")

    boolean_keys = (
        "patient_fact_support",
        "relevant_evidence_available",
        "no_critical_missing_discriminator",
        "no_unsupported_assumption",
    )
    if any(type(payload[key]) is not bool for key in boolean_keys):
        raise ValueError("sufficiency prerequisites must be JSON booleans")
    if not isinstance(payload["rationale"], str):
        raise ValueError("sufficiency rationale must be a string")
    missing = payload["missing_information"]
    if (
        not isinstance(missing, list)
        or any(not isinstance(item, str) or not item.strip() for item in missing)
    ):
        raise ValueError("missing_information must contain concrete strings")

    c3 = payload["no_critical_missing_discriminator"]
    if c3 and missing:
        raise ValueError("C3 true requires empty missing_information")
    if not c3 and not missing:
        raise ValueError("C3 false requires a concrete missing discriminator")

    return SufficiencyResult(
        patient_fact_support=payload["patient_fact_support"],
        relevant_evidence_available=payload["relevant_evidence_available"],
        no_critical_missing_discriminator=c3,
        no_unsupported_assumption=payload["no_unsupported_assumption"],
        rationale=payload["rationale"],
        missing_information=missing,
    )


def _fail_closed() -> SufficiencyResult:
    return SufficiencyResult(
        patient_fact_support=False,
        relevant_evidence_available=False,
        no_critical_missing_discriminator=True,
        no_unsupported_assumption=False,
        rationale="Invalid structured sufficiency response after one repair attempt.",
        missing_information=[],
    )


def evaluate_sufficiency(
    patient: PatientState,
    evidence: list[EvidenceChunk],
    reasoning: ReasoningResult,
    model_call: SufficiencyModelCall,
) -> SufficiencyResult:
    prompt = build_sufficiency_prompt(patient, evidence, reasoning)
    first_response = model_call(prompt)
    try:
        return _parse_sufficiency_response(first_response)
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        repair_prompt = (
            prompt
            + "\n\nREPAIR REQUEST\nThe previous response was invalid or internally "
            + "inconsistent. Return one complete corrected JSON object using exactly "
            + "the required keys and C3/missing_information consistency. Do not add "
            + "facts and do not add commentary outside JSON.\nPREVIOUS RESPONSE\n"
            + first_response
        )
        try:
            return _parse_sufficiency_response(model_call(repair_prompt))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return _fail_closed()


def decide_sufficiency_route(
    slm_a_sufficiency: SufficiencyResult,
    slm_b_sufficiency: SufficiencyResult,
) -> SufficiencyRoute:
    proceed_to_scoring = (
        slm_a_sufficiency.is_sufficient and slm_b_sufficiency.is_sufficient
    )
    if proceed_to_scoring:
        return SufficiencyRoute.PROCEED_TO_VALIDATION
    return SufficiencyRoute.FOLLOW_UP
