import inspect
import json
import unittest

from core.config import DEFAULT_CONFIG
from core.reasoning import ReasoningResult, reason_with_slm_a, reason_with_slm_b
from core.schemas import EvidenceChunk, PatientState


def shared_inputs() -> tuple[PatientState, list[EvidenceChunk]]:
    patient = PatientState(
        chief_complaint="Burning sensation during urination",
        symptoms=["dysuria", "frequency", "urgency"],
        age=28,
        gender="female",
        duration="2 days",
    )
    evidence = [
        EvidenceChunk(
            source="synthetic-source",
            title="Synthetic evidence",
            chunk_id="shared-chunk-1",
            content="Synthetic content for reasoning interface tests.",
        )
    ]
    return patient, evidence


def response_for(name: str) -> str:
    return json.dumps(
        {
            "candidate_diagnoses": [{"name": name, "probability": 0.8}],
            "reasoning_summary": "Synthetic structured reasoning.",
            "confidence": 0.8,
            "evidence_references": [
                {"source": "shared-chunk-1", "support": "Synthetic support."}
            ],
        }
    )


class DualReasoningTests(unittest.TestCase):
    def test_same_shared_inputs(self):
        patient, evidence = shared_inputs()
        prompts: dict[str, str] = {}

        def call_a(prompt: str) -> str:
            prompts["a"] = prompt
            return response_for("Candidate A")

        def call_b(prompt: str) -> str:
            prompts["b"] = prompt
            return response_for("Candidate B")

        reason_with_slm_a(patient, evidence, call_a)
        reason_with_slm_b(patient, evidence, call_b)

        for prompt in prompts.values():
            self.assertIn("Burning sensation during urination", prompt)
            self.assertIn("dysuria, frequency, urgency", prompt)
            self.assertIn("shared-chunk-1", prompt)

    def test_blind_independence(self):
        patient, evidence = shared_inputs()
        prompts: dict[str, str] = {}

        def call_a(prompt: str) -> str:
            prompts["a"] = prompt
            return response_for("A_ONLY_OUTPUT")

        def call_b(prompt: str) -> str:
            prompts["b"] = prompt
            return response_for("B_ONLY_OUTPUT")

        reason_with_slm_a(patient, evidence, call_a)
        reason_with_slm_b(patient, evidence, call_b)

        self.assertNotIn("B_ONLY_OUTPUT", prompts["a"])
        self.assertNotIn("A_ONLY_OUTPUT", prompts["b"])
        expected_parameters = ["patient", "evidence", "model_call"]
        self.assertEqual(
            list(inspect.signature(reason_with_slm_a).parameters), expected_parameters
        )
        self.assertEqual(
            list(inspect.signature(reason_with_slm_b).parameters), expected_parameters
        )

    def test_structured_parsing(self):
        patient, evidence = shared_inputs()
        result_a = reason_with_slm_a(
            patient, evidence, lambda prompt: response_for("Candidate A")
        )
        result_b = reason_with_slm_b(
            patient, evidence, lambda prompt: response_for("Candidate B")
        )

        self.assertIsInstance(result_a, ReasoningResult)
        self.assertIsInstance(result_b, ReasoningResult)
        self.assertEqual(type(result_a), type(result_b))
        self.assertEqual(result_a.model, DEFAULT_CONFIG.slm_a_model)
        self.assertEqual(result_b.model, DEFAULT_CONFIG.slm_b_model)


if __name__ == "__main__":
    unittest.main()
