from unittest import TestCase

from core.adapters.medcpt_faiss import MedCPTFAISS
from core.adapters.ollama_client import OllamaClient
from core.config import DEFAULT_CONFIG
from core.pipeline import create_real_pipeline
from core.reasoning import reason_with_slm_a, reason_with_slm_b
from core.schemas import PatientState, PipelineStatus


class RealServiceSmokeTests(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.store = MedCPTFAISS("corpus/guidelines", "corpus/index")
        cls.client = OllamaClient()
        cls.patient = PatientState(
            chief_complaint="burning during urination",
            symptoms=["dysuria", "frequency", "urgency"],
            age=28,
            gender="female",
            duration="2 days",
            explicit_negations=["medical_history", "allergies", "medications"],
        )
        cls.evidence = cls.store.search(
            "adult woman dysuria urinary frequency urgency guideline", 5
        )

    def test_real_retrieval_returns_metadata(self) -> None:
        self.assertTrue(self.evidence)
        chunk = self.evidence[0]
        self.assertTrue(
            chunk.source
            and chunk.title
            and chunk.chunk_id
            and chunk.content
            and chunk.page is not None
            and chunk.section
            and chunk.retrieval_score is not None
        )

    def test_real_independent_a_b_calls_are_parseable(self) -> None:
        result_a = reason_with_slm_a(
            self.patient,
            self.evidence,
            lambda prompt: self.client.generate(
                prompt, DEFAULT_CONFIG.slm_a_model, json_mode=True
            ),
        )
        result_b = reason_with_slm_b(
            self.patient,
            self.evidence,
            lambda prompt: self.client.generate(
                prompt, DEFAULT_CONFIG.slm_b_model, json_mode=True
            ),
        )

        self.assertEqual(result_a.model, DEFAULT_CONFIG.slm_a_model)
        self.assertEqual(result_b.model, DEFAULT_CONFIG.slm_b_model)

    def test_one_real_end_to_end_case(self) -> None:
        pipeline = create_real_pipeline(self.patient, lambda _question: "No")

        result = pipeline.run()

        self.assertIn(result.status, set(PipelineStatus))
        stages = {item["stage"] for item in pipeline.trace}
        self.assertTrue({"retrieval", "slm_a", "slm_b", "sufficiency"} <= stages)
