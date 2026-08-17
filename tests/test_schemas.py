import unittest

from core.schemas import (
    DCSDecision,
    DCSResult,
    DiagnosisCandidate,
    EvidenceChunk,
    EvidenceReference,
    KASResult,
    LCSResult,
    PatientState,
    PipelineResult,
    PipelineStatus,
    SLMOutput,
    SLMStatus,
    SufficiencyResult,
)


def sufficient_result() -> SufficiencyResult:
    return SufficiencyResult(
        patient_fact_support=True,
        relevant_evidence_available=True,
        no_critical_missing_discriminator=True,
        no_unsupported_assumption=True,
        rationale="All criteria are satisfied.",
        missing_information=[],
    )


def insufficient_result() -> SufficiencyResult:
    return SufficiencyResult(
        patient_fact_support=True,
        relevant_evidence_available=True,
        no_critical_missing_discriminator=False,
        no_unsupported_assumption=True,
        rationale="A critical discriminator is missing.",
        missing_information=["critical discriminator"],
    )


def diagnostic_output(model: str) -> SLMOutput:
    return SLMOutput(
        model=model,
        status=SLMStatus.DIAGNOSTIC_OUTPUT,
        diagnoses=[DiagnosisCandidate(name="Example candidate", probability=0.8)],
        reasoning="Inline schema test reasoning.",
        confidence=0.8,
        evidence=[EvidenceReference(source="Example source", support="Example support")],
        sufficiency=sufficient_result(),
    )


class SchemaTests(unittest.TestCase):
    def test_patient_explicit_negation(self):
        patient = PatientState(
            chief_complaint="Burning sensation during urination",
            symptoms=["dysuria", "frequency", "urgency"],
            explicit_negations=["fever"],
        )
        self.assertIn("fever", patient.explicit_negations)

    def test_invalid_age(self):
        with self.assertRaises(ValueError):
            PatientState(age=-1)

    def test_evidence_metadata(self):
        evidence = EvidenceChunk(
            source="Clinical guideline",
            title="Example evidence",
            page=4,
            section="Assessment",
            chunk_id="chunk-1",
            content="Example content",
            retrieval_score=1.25,
            matched_query="example query",
        )
        self.assertEqual(evidence.source, "Clinical guideline")
        self.assertEqual(evidence.title, "Example evidence")
        self.assertEqual(evidence.page, 4)
        self.assertEqual(evidence.section, "Assessment")
        self.assertEqual(evidence.chunk_id, "chunk-1")
        self.assertEqual(evidence.content, "Example content")
        self.assertEqual(evidence.retrieval_score, 1.25)
        self.assertEqual(evidence.matched_query, "example query")

    def test_sufficiency_all_true(self):
        result = sufficient_result()
        self.assertTrue(result.is_sufficient)
        self.assertEqual(result.status, "SUFFICIENT")

    def test_sufficiency_one_criterion_false(self):
        result = insufficient_result()
        self.assertFalse(result.is_sufficient)
        self.assertEqual(result.status, "INSUFFICIENT")

    def test_insufficient_slm_may_return_no_diagnosis(self):
        output = SLMOutput(
            model="test-model",
            status=SLMStatus.INSUFFICIENT_INFORMATION,
            diagnoses=[],
            reasoning="",
            confidence=0.2,
            evidence=[],
            sufficiency=insufficient_result(),
        )
        self.assertEqual(output.diagnoses, [])

    def test_sufficient_slm_cannot_have_empty_diagnosis(self):
        with self.assertRaises(ValueError):
            SLMOutput(
                model="test-model",
                status=SLMStatus.DIAGNOSTIC_OUTPUT,
                diagnoses=[],
                reasoning="Reasoning is present.",
                confidence=0.8,
                evidence=[],
                sufficiency=sufficient_result(),
            )

    def test_invalid_slm_status(self):
        with self.assertRaises(ValueError):
            SLMStatus("UNKNOWN")

    def test_invalid_confidence(self):
        with self.assertRaises(ValueError):
            SLMOutput(
                model="test-model",
                status=SLMStatus.INSUFFICIENT_INFORMATION,
                diagnoses=[],
                reasoning="",
                confidence=1.5,
                evidence=[],
                sufficiency=insufficient_result(),
            )

    def test_kas_range(self):
        for score in (0.0, 0.5, 1.0):
            with self.subTest(score=score):
                self.assertEqual(KASResult(score).score, score)
        for score in (-0.1, 1.1):
            with self.subTest(score=score):
                with self.assertRaises(ValueError):
                    KASResult(score)

    def test_lcs_range(self):
        for score in (0, 1, 2, 3):
            with self.subTest(score=score):
                self.assertEqual(LCSResult(score).score, score)
        for score in (-1, 4, 2.5):
            with self.subTest(score=score):
                with self.assertRaises(ValueError):
                    LCSResult(score)

    def test_dcs_range(self):
        for score in (0.0, 0.75, 1.0):
            with self.subTest(score=score):
                result = DCSResult(score=score, decision=DCSDecision.APPROVED)
                self.assertEqual(result.score, score)
        for score in (-0.01, 1.01):
            with self.subTest(score=score):
                with self.assertRaises(ValueError):
                    DCSResult(score=score, decision=DCSDecision.FOLLOW_UP)

    def test_approved_pipeline_requires_validation_results(self):
        with self.assertRaises(ValueError):
            PipelineResult(status=PipelineStatus.APPROVED, patient_info=PatientState())

    def test_valid_approved_pipeline_result(self):
        patient = PatientState(
            chief_complaint="Burning sensation during urination",
            symptoms=["dysuria", "frequency", "urgency"],
            explicit_negations=["fever"],
        )
        result = PipelineResult(
            status=PipelineStatus.APPROVED,
            patient_info=patient,
            candidate_diagnoses=[
                DiagnosisCandidate(name="Example candidate", probability=0.8)
            ],
            reasoning_summary="Inline schema test summary.",
            supporting_evidence=[
                EvidenceReference(source="Example source", support="Example support")
            ],
            slm_a_output=diagnostic_output("slm-a"),
            slm_b_output=diagnostic_output("slm-b"),
            kas=KASResult(score=0.8),
            lcs=LCSResult(score=3),
            dcs=DCSResult(score=0.8, decision=DCSDecision.APPROVED),
        )
        self.assertEqual(result.status, PipelineStatus.APPROVED)


if __name__ == "__main__":
    unittest.main()
