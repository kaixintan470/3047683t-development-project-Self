from unittest import TestCase

from core.pipeline import ClinicalPipeline, PipelineDependencies
from core.reasoning import ReasoningResult
from core.schemas import (
    DCSDecision,
    DCSResult,
    DiagnosisCandidate,
    EvidenceChunk,
    EvidenceReference,
    KASResult,
    LCSResult,
    PatientState,
    PipelineStatus,
    SufficiencyResult,
)


def complete_patient() -> PatientState:
    return PatientState(
        chief_complaint="dysuria",
        symptoms=["frequency"],
        age=28,
        gender="female",
        duration="2 days",
        explicit_negations=["medical_history", "allergies", "medications"],
    )


def reasoning(model: str) -> ReasoningResult:
    return ReasoningResult(
        model=model,
        candidate_diagnoses=[DiagnosisCandidate("candidate", 0.8)],
        reasoning_summary="Evidence-supported reasoning.",
        confidence=0.8,
        evidence_references=[EvidenceReference("guideline", "support")],
    )


def sufficient(value: bool) -> SufficiencyResult:
    return SufficiencyResult(
        patient_fact_support=True,
        relevant_evidence_available=True,
        no_critical_missing_discriminator=value,
        no_unsupported_assumption=True,
        rationale="complete" if value else "missing duration detail",
        missing_information=[] if value else ["duration detail"],
    )


def dependencies(counters: dict[str, int], become_sufficient: bool = True) -> PipelineDependencies:
    def retrieve(_queries: list[str]) -> list[EvidenceChunk]:
        counters["retrieval"] += 1
        return [EvidenceChunk("official", "guideline", "c1", "evidence", retrieval_score=0.9)]

    def reason_a(_patient: PatientState, _evidence: list[EvidenceChunk]) -> ReasoningResult:
        counters["a"] += 1
        return reasoning("A")

    def reason_b(_patient: PatientState, _evidence: list[EvidenceChunk]) -> ReasoningResult:
        counters["b"] += 1
        return reasoning("B")

    def check(_patient: PatientState, _evidence: list[EvidenceChunk], result: ReasoningResult) -> SufficiencyResult:
        if result.model == "A" or counters["retrieval"] > 1:
            return sufficient(True)
        return sufficient(become_sufficient and counters["retrieval"] > 1)

    return PipelineDependencies(
        generate_queries=lambda _patient: ["query 1", "query 2"],
        retrieve=retrieve,
        reason_slm_a=reason_a,
        reason_slm_b=reason_b,
        check_sufficiency=check,
        calculate_kas=lambda _claims, _evidence: KASResult(0.8, "supported"),
        evaluate_lcs=lambda _patient, _evidence, _reasoning: LCSResult(3, "consistent"),
        calculate_dcs=lambda kas, lcs: DCSResult(
            0.75 * kas + 0.25 * (lcs / 3), DCSDecision.APPROVED
        ),
        generate_followup_questions=lambda _missing: ["Could you provide that detail?"],
        answer_followup=lambda _question: "provided",
    )


class PipelineTests(TestCase):
    def test_direct_approval_path(self) -> None:
        counters = {"retrieval": 0, "a": 0, "b": 0}
        deps = dependencies(counters)
        deps = PipelineDependencies(**{**deps.__dict__, "check_sufficiency": lambda *_args: sufficient(True)})

        result = ClinicalPipeline(complete_patient(), deps).run()

        self.assertEqual(result.status, PipelineStatus.APPROVED)
        self.assertEqual(result.follow_up_rounds, 0)

    def test_insufficient_then_approved_reruns_retrieval_and_slms(self) -> None:
        counters = {"retrieval": 0, "a": 0, "b": 0}

        result = ClinicalPipeline(complete_patient(), dependencies(counters)).run()

        self.assertEqual(result.status, PipelineStatus.APPROVED)
        self.assertEqual(counters, {"retrieval": 2, "a": 2, "b": 2})

    def test_maximum_rounds_unresolved_without_forced_diagnosis(self) -> None:
        counters = {"retrieval": 0, "a": 0, "b": 0}
        deps = dependencies(counters, become_sufficient=False)
        deps = PipelineDependencies(**{**deps.__dict__, "check_sufficiency": lambda *_args: sufficient(False)})

        result = ClinicalPipeline(complete_patient(), deps).run()

        self.assertEqual(result.status, PipelineStatus.UNRESOLVED_INSUFFICIENT_INFORMATION)
        self.assertEqual(result.candidate_diagnoses, [])
        self.assertEqual(result.follow_up_rounds, 3)
