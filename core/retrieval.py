"""Focused query generation and deterministic retrieval orchestration."""

from collections.abc import Callable
from dataclasses import replace
import json
import re

from core.config import DEFAULT_CONFIG
from core.schemas import EvidenceChunk, PatientState


QueryModel = Callable[[str], str]
RetrievalBackend = Callable[[str, int], list[EvidenceChunk]]
INVALID_QUERY_PATTERNS = (
    re.compile(r"```"),
    re.compile(r"\b(?:SELECT|FROM|WHERE|JOIN|INSERT|UPDATE|DELETE)\b", re.IGNORECASE),
    re.compile(r"\b(?:AND|OR|NOT)\b"),
    re.compile(r"\b[a-zA-Z_][\w-]*\s*:\s*\S"),
)


def build_query_prompt(patient: PatientState) -> str:
    """Build a JSON query prompt from confirmed structured patient facts only."""
    facts: list[str] = []
    field_names = (
        "chief_complaint",
        "symptoms",
        "age",
        "gender",
        "duration",
        "medical_history",
        "allergies",
        "medications",
    )

    for field_name in field_names:
        value = getattr(patient, field_name)
        if value or value == 0:
            rendered = ", ".join(value) if isinstance(value, list) else str(value)
            facts.append(f"{field_name}: {rendered}")
        elif field_name in patient.explicit_negations:
            facts.append(f"{field_name}: confirmed absent")

    for field_name, value in patient.follow_up_answers.items():
        if value:
            facts.append(f"{field_name}: {value}")

    fact_text = "\n".join(facts) if facts else "No confirmed patient facts."
    return (
        "Generate 2 to 3 concise medical guideline retrieval queries using only "
        "the confirmed patient facts below. Target symptom and differential evidence "
        "in the clinical guideline corpus. Do not present an unsupported diagnosis "
        "as a confirmed patient fact. Queries must contain no SQL, Markdown code "
        "fences, search-engine field syntax, or Boolean-query formatting. Return "
        "only one JSON object with no other keys or commentary: "
        '{"queries": ["focused medical query", "focused medical query"]}.\n\n'
        f"CONFIRMED PATIENT FACTS\n{fact_text}"
    )


def _parse_queries(response: str) -> list[str]:
    payload = json.loads(response)
    if not isinstance(payload, dict) or set(payload) != {"queries"}:
        raise ValueError("query response must contain only a queries key")
    raw_queries = payload["queries"]
    if not isinstance(raw_queries, list) or any(
        not isinstance(query, str) for query in raw_queries
    ):
        raise ValueError("queries must be a JSON string array")

    queries: list[str] = []
    seen: set[str] = set()
    for raw_query in raw_queries:
        query = " ".join(raw_query.split())
        if not query:
            continue
        if any(pattern.search(query) for pattern in INVALID_QUERY_PATTERNS):
            raise ValueError("query contains disallowed SQL, code, field, or Boolean syntax")
        key = query.casefold()
        if key not in seen:
            seen.add(key)
            queries.append(query)
        if len(queries) == DEFAULT_CONFIG.query_count:
            break

    if not 2 <= len(queries) <= DEFAULT_CONFIG.query_count:
        raise ValueError(
            f"query generation must return 2 to {DEFAULT_CONFIG.query_count} queries"
        )
    return queries


def generate_retrieval_queries(
    patient: PatientState,
    model: QueryModel,
) -> list[str]:
    """Request clean JSON queries, retrying the same model once when invalid."""
    prompt = build_query_prompt(patient)
    first_response = model(prompt)
    try:
        return _parse_queries(first_response)
    except (json.JSONDecodeError, TypeError, ValueError):
        repair_prompt = (
            prompt
            + "\n\nREPAIR REQUEST\nThe previous response was invalid. Return only "
            + "the required JSON object with 2 to 3 concise, unique, plain-language "
            + "medical queries. Remove SQL, code fences, field syntax, Boolean "
            + "formatting, empty entries, and duplicates.\nPREVIOUS RESPONSE\n"
            + first_response
        )
        return _parse_queries(model(repair_prompt))


def _score(chunk: EvidenceChunk) -> float:
    return chunk.retrieval_score if chunk.retrieval_score is not None else float("-inf")


def retrieve_evidence(
    queries: list[str],
    backend: RetrievalBackend,
) -> list[EvidenceChunk]:
    """Merge, deduplicate, rank, and return the configured final Top-K evidence."""
    best_by_chunk_id: dict[str, EvidenceChunk] = {}

    for query in queries:
        for chunk in backend(query, DEFAULT_CONFIG.retrieval_top_k):
            matched_chunk = replace(chunk, matched_query=query)
            current = best_by_chunk_id.get(matched_chunk.chunk_id)
            if current is None or _score(matched_chunk) > _score(current):
                best_by_chunk_id[matched_chunk.chunk_id] = matched_chunk

    ranked = sorted(best_by_chunk_id.values(), key=_score, reverse=True)
    return ranked[: DEFAULT_CONFIG.retrieval_top_k]
