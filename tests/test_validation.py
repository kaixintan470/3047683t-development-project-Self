import unittest

from core.reasoning import ReasoningResult
from core.schemas import DiagnosisCandidate, EvidenceChunk, PatientState
from core.validation.kas import calculate_kas
from core.validation.lcs import evaluate_lcs


def synthetic_evidence() -> list[EvidenceChunk]:
    return [
        EvidenceChunk(
            source="synthetic-source",
            title="Synthetic evidence",
            chunk_id="validation-chunk",
            content="Synthetic support content.",
        )
    ]


class ValidationTests(unittest.TestCase):
    def test_supported_vs_unsupported_kas(self):
        evidence = synthetic_evidence()

        def similarity(claim: str, chunks: list[EvidenceChunk]) -> float:
            return 1.0 if claim == "supported claim" else 0.0

        def relation(claim: str, chunks: list[EvidenceChunk]) -> float:
            return 1.0 if claim == "supported claim" else 0.0

        supported = calculate_kas(
            ["supported claim"], evidence, similarity, relation, lambda claim: 1.0
        )
        unsupported = calculate_kas(
            ["unsupported claim"], evidence, similarity, relation, lambda claim: 1.0
        )
        self.assertGreater(supported.score, unsupported.score)

    def test_kas_range(self):
        result = calculate_kas(
            ["claim one", "claim two"],
            synthetic_evidence(),
            lambda claim, chunks: 0.6,
            lambda claim, chunks: 0.4,
            lambda claim: 0.8,
        )
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 1.0)

    def test_lcs_discrete_score(self):
        patient = PatientState(chief_complaint="Synthetic complaint")
        evidence = synthetic_evidence()
        reasoning = ReasoningResult(
            model="test-model",
            candidate_diagnoses=[DiagnosisCandidate("Candidate", 0.7)],
            reasoning_summary="Synthetic reasoning.",
            confidence=0.7,
            evidence_references=[],
        )
        coherent = evaluate_lcs(
            patient,
            evidence,
            reasoning,
            lambda prompt: {"score": 3, "rationale": "Coherent."},
        )
        contradictory = evaluate_lcs(
            patient,
            evidence,
            reasoning,
            lambda prompt: {"score": 0, "rationale": "Contradictory."},
        )
        self.assertGreater(coherent.score, contradictory.score)
        self.assertIn(coherent.score, (0, 1, 2, 3))
        self.assertIn(contradictory.score, (0, 1, 2, 3))


if __name__ == "__main__":
    unittest.main()
