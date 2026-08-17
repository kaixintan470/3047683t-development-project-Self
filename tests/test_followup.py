import unittest

from core.config import DEFAULT_CONFIG
from core.followup import (
    FollowupStatus,
    generate_followup_questions,
    merge_missing_information,
    run_followup_loop,
)
from core.schemas import PatientState, SufficiencyResult


def sufficiency(is_sufficient: bool, missing: list[str]) -> SufficiencyResult:
    return SufficiencyResult(
        patient_fact_support=True,
        relevant_evidence_available=True,
        no_critical_missing_discriminator=is_sufficient,
        no_unsupported_assumption=True,
        rationale="Synthetic sufficiency result.",
        missing_information=missing,
    )


class FollowupTests(unittest.TestCase):
    def test_neutral_question(self):
        captured: dict[str, str] = {}

        def fake_model(prompt: str) -> str:
            captured["prompt"] = prompt
            return "Do you currently have a fever?"

        missing = merge_missing_information(["fever"], ["fever"])
        questions = generate_followup_questions(missing, fake_model)

        self.assertEqual(missing, ["fever"])
        self.assertNotIn("urinary tract infection", questions[0].casefold())
        self.assertNotIn("model reasoning", questions[0].casefold())
        self.assertIn("Do not reveal or mention any diagnosis", captured["prompt"])

    def test_update_and_rerun(self):
        patient = PatientState(
            chief_complaint="Burning sensation during urination",
            symptoms=["dysuria"],
        )
        patient_identity = id(patient)
        calls = {"retrieval": 1, "a": 1, "b": 1}
        insufficient = sufficiency(False, ["duration"])
        sufficient = sufficiency(True, [])

        def retrieval(current_patient: PatientState) -> list[str]:
            calls["retrieval"] += 1
            self.assertEqual(id(current_patient), patient_identity)
            return ["evidence"]

        def model_a(current_patient: PatientState, evidence: object) -> str:
            calls["a"] += 1
            return "a"

        def model_b(current_patient: PatientState, evidence: object) -> str:
            calls["b"] += 1
            return "b"

        result = run_followup_loop(
            patient,
            insufficient,
            insufficient,
            retrieval,
            model_a,
            model_b,
            lambda current, evidence, a, b: (sufficient, sufficient),
            lambda missing: ["How long have you had these symptoms?"],
            lambda question: "2 days",
        )

        self.assertEqual(id(result.patient), patient_identity)
        self.assertEqual(patient.duration, "2 days")
        self.assertEqual(calls, {"retrieval": 2, "a": 2, "b": 2})
        self.assertEqual(result.status, FollowupStatus.PROCEED_TO_VALIDATION)

    def test_maximum_rounds(self):
        patient = PatientState()
        insufficient = sufficiency(False, ["duration"])
        calls = {"retrieval": 0, "a": 0, "b": 0}

        def retrieval(current_patient: PatientState) -> list[str]:
            calls["retrieval"] += 1
            return []

        def model_a(current_patient: PatientState, evidence: object) -> str:
            calls["a"] += 1
            return "a"

        def model_b(current_patient: PatientState, evidence: object) -> str:
            calls["b"] += 1
            return "b"

        result = run_followup_loop(
            patient,
            insufficient,
            insufficient,
            retrieval,
            model_a,
            model_b,
            lambda current, evidence, a, b: (insufficient, insufficient),
            lambda missing: ["How long have you had these symptoms?"],
            lambda question: "still unknown",
        )

        self.assertEqual(
            result.status,
            FollowupStatus.UNRESOLVED_INSUFFICIENT_INFORMATION,
        )
        self.assertEqual(result.follow_up_rounds, DEFAULT_CONFIG.max_followup_rounds)
        self.assertEqual(calls["retrieval"], DEFAULT_CONFIG.max_followup_rounds)
        self.assertEqual(calls["a"], DEFAULT_CONFIG.max_followup_rounds)
        self.assertEqual(calls["b"], DEFAULT_CONFIG.max_followup_rounds)


if __name__ == "__main__":
    unittest.main()
