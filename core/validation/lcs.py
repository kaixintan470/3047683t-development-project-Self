"""Injected local-judge interface for Logic Consistency Score."""

from collections.abc import Callable
from dataclasses import asdict
import json

from core.reasoning import ReasoningResult
from core.schemas import EvidenceChunk, LCSResult, PatientState


LocalJudge = Callable[[str], str | dict[str, object]]


def build_lcs_prompt(
    patient: PatientState,
    evidence: list[EvidenceChunk],
    reasoning: ReasoningResult,
) -> str:
    return (
        "Evaluate the reasoning using exactly four checks: (1) use of explicit "
        "patient facts, (2) use of retrieved evidence, (3) reasoning coherence "
        "and contradiction, and (4) conclusion support. Return JSON with an "
        "integer score from 0 to 3 and a short rationale.\n\n"
        f"PATIENT\n{json.dumps(asdict(patient), sort_keys=True)}\n\n"
        f"EVIDENCE\n{json.dumps([asdict(item) for item in evidence], sort_keys=True)}\n\n"
        f"REASONING\n{json.dumps(asdict(reasoning), sort_keys=True)}"
    )


def evaluate_lcs(
    patient: PatientState,
    evidence: list[EvidenceChunk],
    reasoning: ReasoningResult,
    judge: LocalJudge,
) -> LCSResult:
    response = judge(build_lcs_prompt(patient, evidence, reasoning))
    payload = json.loads(response) if isinstance(response, str) else response
    return LCSResult(
        score=payload["score"],
        rationale=str(payload.get("rationale", "Local judge supplied no rationale.")),
    )
