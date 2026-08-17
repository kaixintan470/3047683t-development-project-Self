"""Independent pre-sufficiency reasoning paths for SLM-A and SLM-B."""

from collections.abc import Callable
from dataclasses import dataclass
import json

from core.config import DEFAULT_CONFIG
from core.schemas import (
    DiagnosisCandidate,
    EvidenceChunk,
    EvidenceReference,
    PatientState,
)


ModelCall = Callable[[str], str]


@dataclass
class ReasoningResult:
    model: str
    candidate_diagnoses: list[DiagnosisCandidate]
    reasoning_summary: str
    confidence: float
    evidence_references: list[EvidenceReference]

    def __post_init__(self) -> None:
        if not self.model:
            raise ValueError("model must not be empty")
        if not 0 <= self.confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")


@dataclass(frozen=True)
class ReasoningService:
    model: str

    def build_prompt(
        self,
        patient: PatientState,
        evidence: list[EvidenceChunk],
    ) -> str:
        patient_facts: list[str] = []
        for field_name in (
            "chief_complaint",
            "symptoms",
            "age",
            "gender",
            "duration",
            "medical_history",
            "allergies",
            "medications",
        ):
            value = getattr(patient, field_name)
            if value or value == 0:
                rendered = ", ".join(value) if isinstance(value, list) else str(value)
                patient_facts.append(f"{field_name}: {rendered}")
            elif field_name in patient.explicit_negations:
                patient_facts.append(f"{field_name}: confirmed absent")

        for field_name, value in patient.follow_up_answers.items():
            if value:
                patient_facts.append(f"{field_name}: {value}")

        evidence_blocks = [
            (
                f"chunk_id: {chunk.chunk_id}\n"
                f"source: {chunk.source}\n"
                f"title: {chunk.title}\n"
                f"content: {chunk.content}"
            )
            for chunk in evidence
        ]
        return (
            f"You are reasoning independently as model {self.model}. Use only the "
            "shared patient facts and evidence below. Return only JSON in this "
            "shape: {\"candidate_diagnoses\": [{\"name\": \"...\", "
            "\"probability\": 0.0}], \"reasoning_summary\": \"...\", "
            "\"confidence\": 0.0, \"evidence_references\": "
            "[{\"source\": \"...\", \"support\": \"...\"}]}. All "
            "probabilities and confidence values must be between 0 and 1.\n\n"
            "PATIENT FACTS\n"
            + "\n".join(patient_facts)
            + "\n\nEVIDENCE\n"
            + "\n\n".join(evidence_blocks)
        )

    def reason(
        self,
        patient: PatientState,
        evidence: list[EvidenceChunk],
        model_call: ModelCall,
    ) -> ReasoningResult:
        response = model_call(self.build_prompt(patient, evidence))
        return parse_reasoning_response(response, self.model)


def parse_reasoning_response(response: str, model: str) -> ReasoningResult:
    payload = json.loads(response)
    diagnoses = [
        DiagnosisCandidate(name=item["name"], probability=item["probability"])
        for item in payload["candidate_diagnoses"]
    ]
    references = [
        EvidenceReference(source=item["source"], support=item["support"])
        for item in payload["evidence_references"]
    ]
    return ReasoningResult(
        model=model,
        candidate_diagnoses=diagnoses,
        reasoning_summary=payload["reasoning_summary"],
        confidence=payload["confidence"],
        evidence_references=references,
    )


SLM_A_REASONER = ReasoningService(DEFAULT_CONFIG.slm_a_model)
SLM_B_REASONER = ReasoningService(DEFAULT_CONFIG.slm_b_model)


def reason_with_slm_a(
    patient: PatientState,
    evidence: list[EvidenceChunk],
    model_call: ModelCall,
) -> ReasoningResult:
    return SLM_A_REASONER.reason(patient, evidence, model_call)


def reason_with_slm_b(
    patient: PatientState,
    evidence: list[EvidenceChunk],
    model_call: ModelCall,
) -> ReasoningResult:
    return SLM_B_REASONER.reason(patient, evidence, model_call)
