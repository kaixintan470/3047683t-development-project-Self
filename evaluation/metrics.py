"""Regenerate Chapter 4 summary metrics from saved run records."""

from collections import Counter
import json
from pathlib import Path
from typing import Any


def regenerate_metrics(results_path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(results_path).read_text(encoding="utf-8"))
    records = payload["records"]
    total = len(records)
    divisor = total or 1
    statuses = Counter(record["final_status"] for record in records)

    return {
        "cases_processed": total,
        "final_status_counts": dict(statuses),
        "average_latency_seconds": sum(
            record["latency_seconds"] for record in records
        )
        / divisor,
        "average_retrieved_chunks": sum(
            record["retrieval"]["chunks_returned"] for record in records
        )
        / divisor,
        "average_follow_up_rounds": sum(
            record["follow_up_rounds"] for record in records
        )
        / divisor,
        "diagnostic_outcomes_recorded": sum(
            len(record["diagnostic_outcomes"]) for record in records
        ),
        "sufficiency_events_recorded": sum(
            len(record["sufficiency_outcomes"]) for record in records
        ),
        "config": payload["config"],
    }
