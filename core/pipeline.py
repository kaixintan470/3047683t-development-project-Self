"""The single canonical end-to-end clinical pipeline orchestrator."""

from collections.abc import Callable
from dataclasses import dataclass

from core.config import DEFAULT_CONFIG
from core.followup import apply_followup_answer, merge_missing_information
from core.interview import get_missing_interview_fields
from core.reasoning import ReasoningResult
from core.schemas import (
    DCSDecision,
    DCSResult,
    EvidenceChunk,
    KASResult,
    LCSResult,
    PatientState,
    PipelineResult,
    PipelineStatus,
    SLMOutput,
    SLMStatus,
    SufficiencyResult,
)


@dataclass(frozen=True)
class PipelineDependencies:
    generate_queries: Callable[[PatientState], list[str]]
    retrieve: Callable[[list[str]], list[EvidenceChunk]]
    reason_slm_a: Callable[[PatientState, list[EvidenceChunk]], ReasoningResult]
    reason_slm_b: Callable[[PatientState, list[EvidenceChunk]], ReasoningResult]
    check_sufficiency: Callable[
        [PatientState, list[EvidenceChunk], ReasoningResult], SufficiencyResult
    ]
    calculate_kas: Callable[[list[str], list[EvidenceChunk]], KASResult]
    evaluate_lcs: Callable[
        [PatientState, list[EvidenceChunk], ReasoningResult], LCSResult
    ]
    calculate_dcs: Callable[[float, int], DCSResult]
    generate_followup_questions: Callable[[list[str]], list[str]]
    answer_followup: Callable[[str], str]


class ClinicalPipeline:
    """Own state and route one patient through the fixed pipeline."""

    def __init__(
        self,
        patient: PatientState,
        dependencies: PipelineDependencies,
    ) -> None:
        self.patient = patient
        self.dependencies = dependencies
        self.follow_up_rounds = 0
        self.current_stage = "INTERVIEW"
        self.trace: list[dict[str, object]] = []

    @staticmethod
    def _normalise_output(
        reasoning: ReasoningResult,
        sufficiency: SufficiencyResult,
    ) -> SLMOutput:
        status = (
            SLMStatus.DIAGNOSTIC_OUTPUT
            if sufficiency.is_sufficient
            else SLMStatus.INSUFFICIENT_INFORMATION
        )
        return SLMOutput(
            model=reasoning.model,
            status=status,
            diagnoses=reasoning.candidate_diagnoses if sufficiency.is_sufficient else [],
            reasoning=reasoning.reasoning_summary if sufficiency.is_sufficient else "",
            confidence=reasoning.confidence,
            evidence=reasoning.evidence_references,
            sufficiency=sufficiency,
        )

    @staticmethod
    def _combined_reasoning(
        result_a: ReasoningResult,
        result_b: ReasoningResult,
    ) -> ReasoningResult:
        return ReasoningResult(
            model=f"{result_a.model} + {result_b.model}",
            candidate_diagnoses=(
                result_a.candidate_diagnoses + result_b.candidate_diagnoses
            ),
            reasoning_summary=(
                f"SLM-A: {result_a.reasoning_summary}\n"
                f"SLM-B: {result_b.reasoning_summary}"
            ),
            confidence=(result_a.confidence + result_b.confidence) / 2,
            evidence_references=(
                result_a.evidence_references + result_b.evidence_references
            ),
        )

    def _unresolved(self) -> PipelineResult:
        self.current_stage = "UNRESOLVED"
        return PipelineResult(
            status=PipelineStatus.UNRESOLVED_INSUFFICIENT_INFORMATION,
            patient_info=self.patient,
            follow_up_rounds=self.follow_up_rounds,
        )

    def _follow_up(self, missing_information: list[str]) -> bool:
        if self.follow_up_rounds >= DEFAULT_CONFIG.max_followup_rounds:
            return False

        self.current_stage = "FOLLOW_UP"
        questions = self.dependencies.generate_followup_questions(missing_information)
        if not questions or not missing_information:
            return False

        for index, question in enumerate(questions):
            field_name = missing_information[min(index, len(missing_information) - 1)]
            apply_followup_answer(
                self.patient,
                field_name,
                self.dependencies.answer_followup(question),
            )
        self.follow_up_rounds += 1
        return True

    def run(self) -> PipelineResult:
        missing_interview = get_missing_interview_fields(self.patient)
        if missing_interview:
            return PipelineResult(
                status=PipelineStatus.NEED_MORE_INFO,
                patient_info=self.patient,
                validation_notes=", ".join(missing_interview),
                follow_up_rounds=self.follow_up_rounds,
            )

        while True:
            self.current_stage = "QUERY_GENERATION"
            queries = self.dependencies.generate_queries(self.patient)

            self.current_stage = "RETRIEVAL"
            evidence = self.dependencies.retrieve(queries)
            self.trace.append(
                {
                    "stage": "retrieval",
                    "count": len(evidence),
                    "chunk_ids": [chunk.chunk_id for chunk in evidence],
                    "sources": list(dict.fromkeys(chunk.source for chunk in evidence)),
                }
            )

            self.current_stage = "DUAL_REASONING"
            reasoning_a = self.dependencies.reason_slm_a(self.patient, evidence)
            reasoning_b = self.dependencies.reason_slm_b(self.patient, evidence)
            self.trace.append(
                {
                    "stage": "slm_a",
                    "model": reasoning_a.model,
                    "candidate_count": len(reasoning_a.candidate_diagnoses),
                }
            )
            self.trace.append(
                {
                    "stage": "slm_b",
                    "model": reasoning_b.model,
                    "candidate_count": len(reasoning_b.candidate_diagnoses),
                }
            )

            self.current_stage = "SUFFICIENCY"
            sufficiency_a = self.dependencies.check_sufficiency(
                self.patient, evidence, reasoning_a
            )
            sufficiency_b = self.dependencies.check_sufficiency(
                self.patient, evidence, reasoning_b
            )
            self.trace.append(
                {
                    "stage": "sufficiency",
                    "slm_a": sufficiency_a.status,
                    "slm_b": sufficiency_b.status,
                    "slm_a_rationale": sufficiency_a.rationale,
                    "slm_b_rationale": sufficiency_b.rationale,
                    "slm_a_missing": sufficiency_a.missing_information,
                    "slm_b_missing": sufficiency_b.missing_information,
                    "slm_a_criteria": {
                        "c1": sufficiency_a.patient_fact_support,
                        "c2": sufficiency_a.relevant_evidence_available,
                        "c3": sufficiency_a.no_critical_missing_discriminator,
                        "c4": sufficiency_a.no_unsupported_assumption,
                    },
                    "slm_b_criteria": {
                        "c1": sufficiency_b.patient_fact_support,
                        "c2": sufficiency_b.relevant_evidence_available,
                        "c3": sufficiency_b.no_critical_missing_discriminator,
                        "c4": sufficiency_b.no_unsupported_assumption,
                    },
                }
            )

            if not (sufficiency_a.is_sufficient and sufficiency_b.is_sufficient):
                missing = merge_missing_information(
                    sufficiency_a.missing_information,
                    sufficiency_b.missing_information,
                )
                if self._follow_up(missing):
                    continue
                return self._unresolved()

            slm_a_output = self._normalise_output(reasoning_a, sufficiency_a)
            slm_b_output = self._normalise_output(reasoning_b, sufficiency_b)
            combined = self._combined_reasoning(reasoning_a, reasoning_b)
            claims = [
                *[item.name for item in combined.candidate_diagnoses],
                combined.reasoning_summary,
            ]

            self.current_stage = "VALIDATION"
            kas = self.dependencies.calculate_kas(claims, evidence)
            lcs = self.dependencies.evaluate_lcs(self.patient, evidence, combined)
            dcs = self.dependencies.calculate_dcs(kas.score, lcs.score)
            self.trace.append(
                {
                    "stage": "validation",
                    "kas": kas.score,
                    "lcs": lcs.score,
                    "dcs": dcs.score,
                    "decision": dcs.decision.value,
                }
            )

            if dcs.decision == DCSDecision.APPROVED:
                self.current_stage = "APPROVED"
                return PipelineResult(
                    status=PipelineStatus.APPROVED,
                    patient_info=self.patient,
                    candidate_diagnoses=combined.candidate_diagnoses,
                    reasoning_summary=combined.reasoning_summary,
                    supporting_evidence=combined.evidence_references,
                    slm_a_output=slm_a_output,
                    slm_b_output=slm_b_output,
                    kas=kas,
                    lcs=lcs,
                    dcs=dcs,
                    validation_notes=f"KAS: {kas.rationale}; LCS: {lcs.rationale}",
                    follow_up_rounds=self.follow_up_rounds,
                )

            weakness = [
                f"knowledge alignment: {kas.rationale}",
                f"logic consistency: {lcs.rationale}",
            ]
            if not self._follow_up(weakness):
                return self._unresolved()


def create_real_pipeline(
    patient: PatientState,
    answer_followup: Callable[[str], str],
    corpus_dir: str = "corpus/guidelines",
    index_dir: str = "corpus/index",
) -> ClinicalPipeline:
    """Wire the canonical pipeline to the real local adapters."""
    import json

    from core.adapters.medcpt_faiss import MedCPTFAISS
    from core.adapters.ollama_client import OllamaClient
    from core.followup import generate_followup_questions
    from core.reasoning import reason_with_slm_a, reason_with_slm_b
    from core.retrieval import generate_retrieval_queries, retrieve_evidence
    from core.sufficiency import evaluate_sufficiency
    from core.validation.dcs import calculate_dcs
    from core.validation.kas import calculate_kas
    from core.validation.lcs import evaluate_lcs

    client = OllamaClient()
    store = MedCPTFAISS(corpus_dir, index_dir)
    qwen = DEFAULT_CONFIG.slm_a_model

    def json_call(model: str) -> Callable[[str], str]:
        return lambda prompt: client.generate(prompt, model, json_mode=True)

    def evidence_relation(claim: str, evidence: list[EvidenceChunk]) -> float:
        prompt = (
            "Using only the evidence below, return JSON with a probability from "
            "0 to 1 for whether it supports the claim: "
            f"{claim}\n\n" + "\n".join(chunk.content for chunk in evidence)
        )
        payload = json.loads(client.generate(prompt, qwen, json_mode=True))
        return float(payload["probability"])

    def query_model(prompt: str) -> str:
        return client.generate(prompt, qwen, json_mode=True)

    dependencies = PipelineDependencies(
        generate_queries=lambda current: generate_retrieval_queries(
            current, query_model
        ),
        retrieve=lambda queries: retrieve_evidence(queries, store.search),
        reason_slm_a=lambda current, evidence: reason_with_slm_a(
            current, evidence, json_call(DEFAULT_CONFIG.slm_a_model)
        ),
        reason_slm_b=lambda current, evidence: reason_with_slm_b(
            current, evidence, json_call(DEFAULT_CONFIG.slm_b_model)
        ),
        check_sufficiency=lambda current, evidence, reasoning: evaluate_sufficiency(
            current, evidence, reasoning, json_call(qwen)
        ),
        calculate_kas=lambda claims, evidence: calculate_kas(
            claims,
            evidence,
            store.semantic_similarity,
            evidence_relation,
            lambda _claim: 1 / len(claims),
        ),
        evaluate_lcs=lambda current, evidence, reasoning: evaluate_lcs(
            current, evidence, reasoning, json_call(qwen)
        ),
        calculate_dcs=calculate_dcs,
        generate_followup_questions=lambda missing: generate_followup_questions(
            missing, lambda prompt: client.generate(prompt, qwen)
        ),
        answer_followup=answer_followup,
    )
    return ClinicalPipeline(patient, dependencies)
