import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase

from core.config import DEFAULT_CONFIG
from core.schemas import DiagnosisCandidate, PipelineStatus
from evaluation.metrics import regenerate_metrics
from evaluation.runner import run_evaluation


class FakePipeline:
    def __init__(self, patient) -> None:
        self.patient = patient
        self.trace = [
            {"stage": "retrieval", "count": 5},
            {"stage": "slm_a", "model": DEFAULT_CONFIG.slm_a_model},
            {"stage": "slm_b", "model": DEFAULT_CONFIG.slm_b_model},
            {"stage": "sufficiency", "slm_a": "SUFFICIENT", "slm_b": "SUFFICIENT"},
        ]

    def run(self):
        return SimpleNamespace(
            status=PipelineStatus.APPROVED,
            candidate_diagnoses=[DiagnosisCandidate("candidate", 0.8)],
            follow_up_rounds=0,
        )


class EvaluationTests(TestCase):
    def test_tiny_evaluation_processes_all_cases_and_saves_config(self) -> None:
        with TemporaryDirectory() as directory:
            output = Path(directory) / "tiny_results.json"
            payload = run_evaluation(
                "test_data/cases.json", output, lambda patient: FakePipeline(patient)
            )

            self.assertEqual(len(payload["records"]), 2)
            self.assertTrue(output.exists())
            self.assertTrue(all(record["config"] for record in payload["records"]))
            self.assertEqual(payload["config"]["retrieval_top_k"], 5)

    def test_metrics_regenerate_from_saved_results_without_pipeline(self) -> None:
        saved = {
            "config": {"chunk_size": 1000, "retrieval_top_k": 5},
            "records": [
                {
                    "final_status": "APPROVED",
                    "latency_seconds": 1.25,
                    "retrieval": {"chunks_returned": 5},
                    "follow_up_rounds": 1,
                    "diagnostic_outcomes": [{"name": "candidate", "probability": 0.8}],
                    "sufficiency_outcomes": [{"slm_a": "SUFFICIENT", "slm_b": "SUFFICIENT"}],
                }
            ],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "saved.json"
            path.write_text(json.dumps(saved), encoding="utf-8")

            summary = regenerate_metrics(path)

            self.assertEqual(summary["cases_processed"], 1)
            self.assertEqual(summary["final_status_counts"], {"APPROVED": 1})
            self.assertEqual(summary["average_retrieved_chunks"], 5)
