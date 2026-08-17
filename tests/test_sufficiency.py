import json
import unittest

from core.reasoning import ReasoningResult
from core.schemas import DiagnosisCandidate, EvidenceChunk, PatientState, SufficiencyResult
from core.sufficiency import (
    SufficiencyRoute,
    decide_sufficiency_route,
    evaluate_sufficiency,
)


def patient_and_reasoning() -> tuple[
    PatientState, list[EvidenceChunk], ReasoningResult
]:
    patient = PatientState(
        chief_complaint="Burning sensation during urination",
        symptoms=["dysuria", "frequency"],
        explicit_negations=["allergies"],
        follow_up_answers={"fever": "No"},
    )
    evidence = [
        EvidenceChunk(
            source="synthetic-source",
            title="Synthetic evidence",
            chunk_id="sufficiency-chunk",
            content="Synthetic evidence content.",
        )
    ]
    reasoning = ReasoningResult(
        model="test-model",
        candidate_diagnoses=[DiagnosisCandidate("Candidate", 0.8)],
        reasoning_summary="Synthetic reasoning.",
        confidence=0.8,
        evidence_references=[],
    )
    return patient, evidence, reasoning


def model_response(c3: bool, missing: list[str] | None = None) -> str:
    return json.dumps(
        {
            "patient_fact_support": True,
            "relevant_evidence_available": True,
            "no_critical_missing_discriminator": c3,
            "no_unsupported_assumption": True,
            "rationale": "Synthetic sufficiency rationale.",
            "missing_information": ([] if c3 else ["pregnancy status"])
            if missing is None
            else missing,
        }
    )


class SufficiencyTests(unittest.TestCase):
    def test_confirmed_negation_and_followup_are_known(self):
        patient, evidence, reasoning = patient_and_reasoning()
        captured = {}

        def model(prompt: str) -> str:
            captured["prompt"] = prompt
            return model_response(True)

        result = evaluate_sufficiency(patient, evidence, reasoning, model)

        self.assertTrue(result.is_sufficient)
        self.assertIn("CONFIRMED ABSENT", captured["prompt"])
        self.assertIn("allergies: confirmed absent", captured["prompt"])
        self.assertIn("fever: No", captured["prompt"])
        self.assertNotIn("allergies\nfever", captured["prompt"].split("UNKNOWN / NOT YET PROVIDED", 1)[1])

    def test_one_prerequisite_false(self):
        patient, evidence, reasoning = patient_and_reasoning()
        result = evaluate_sufficiency(
            patient, evidence, reasoning, lambda prompt: model_response(False)
        )
        self.assertFalse(result.is_sufficient)
        self.assertEqual(result.missing_information, ["pregnancy status"])

    def test_inconsistent_c3_repairs_once_then_fails_closed(self):
        patient, evidence, reasoning = patient_and_reasoning()
        responses = iter([model_response(False, []), model_response(True)])
        repaired = evaluate_sufficiency(
            patient, evidence, reasoning, lambda prompt: next(responses)
        )
        self.assertTrue(repaired.is_sufficient)

        calls = []
        failed = evaluate_sufficiency(
            patient,
            evidence,
            reasoning,
            lambda prompt: calls.append(prompt) or model_response(False, []),
        )
        self.assertFalse(failed.is_sufficient)
        self.assertEqual(len(calls), 2)
        self.assertEqual(failed.missing_information, [])

    def test_dual_and_rule(self):
        sufficient = SufficiencyResult(True, True, True, True, "Complete.", [])
        insufficient = SufficiencyResult(
            True, True, False, True, "Missing discriminator.", ["detail"]
        )
        self.assertEqual(
            decide_sufficiency_route(sufficient, sufficient),
            SufficiencyRoute.PROCEED_TO_VALIDATION,
        )
        self.assertEqual(
            decide_sufficiency_route(sufficient, insufficient),
            SufficiencyRoute.FOLLOW_UP,
        )


if __name__ == "__main__":
    unittest.main()
