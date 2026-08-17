"""Small, dependency-injected Chapter 4 experiment runner."""

from collections.abc import Callable
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from core.config import DEFAULT_CONFIG
from core.schemas import PatientState


def configuration_metadata() -> dict[str, Any]:
    """Return every fixed baseline parameter used by an evaluation run."""
    return asdict(DEFAULT_CONFIG)


def load_cases(path: str | Path) -> list[dict[str, Any]]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _value(item: object) -> object:
    return getattr(item, "value", item)


def run_evaluation(
    cases_path: str | Path,
    output_path: str | Path,
    pipeline_factory: Callable[[PatientState], object],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []

    for case in load_cases(cases_path):
        patient = PatientState(**case["patient_facts"])
        pipeline = pipeline_factory(patient)
        started = perf_counter()
        result = pipeline.run()
        latency_seconds = perf_counter() - started
        trace = getattr(pipeline, "trace", [])
        retrieval_events = [item for item in trace if item.get("stage") == "retrieval"]
        sufficiency_events = [
            item for item in trace if item.get("stage") == "sufficiency"
        ]

        records.append(
            {
                "case_id": case["case_id"],
                "expected_information_state": case["expected_information_state"],
                "retrieval": {
                    "runs": len(retrieval_events),
                    "chunks_returned": sum(
                        int(item.get("count", 0)) for item in retrieval_events
                    ),
                },
                "sufficiency_outcomes": sufficiency_events,
                "diagnostic_outcomes": [
                    {"name": item.name, "probability": item.probability}
                    for item in result.candidate_diagnoses
                ],
                "follow_up_rounds": result.follow_up_rounds,
                "final_status": _value(result.status),
                "latency_seconds": latency_seconds,
                "config": configuration_metadata(),
            }
        )

    payload = {"config": configuration_metadata(), "records": records}
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return payload
