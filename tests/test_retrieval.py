import json
import unittest

from core.config import DEFAULT_CONFIG
from core.retrieval import generate_retrieval_queries, retrieve_evidence
from core.schemas import EvidenceChunk, PatientState


def evidence(chunk_id: str, score: float) -> EvidenceChunk:
    return EvidenceChunk(
        source="synthetic-guideline",
        title="Synthetic guideline",
        chunk_id=chunk_id,
        content=f"Synthetic evidence for {chunk_id}.",
        retrieval_score=score,
    )


def patient() -> PatientState:
    return PatientState(
        chief_complaint="Burning sensation during urination",
        symptoms=["dysuria", "frequency", "urgency"],
        age=28,
        gender="female",
        duration="2 days",
    )


class RetrievalTests(unittest.TestCase):
    def test_clean_json_queries_remove_empty_and_duplicates(self):
        captured = {}

        def fake_model(prompt: str) -> str:
            captured["prompt"] = prompt
            return json.dumps(
                {
                    "queries": [
                        "female dysuria frequency urgency guideline",
                        "",
                        "Female dysuria frequency urgency guideline",
                        "acute urinary symptoms differential evidence",
                        "urinary burning clinical presentation",
                    ]
                }
            )

        queries = generate_retrieval_queries(patient(), fake_model)

        self.assertEqual(len(queries), 3)
        self.assertEqual(len({query.casefold() for query in queries}), 3)
        self.assertIn('{"queries":', captured["prompt"])
        self.assertEqual(DEFAULT_CONFIG.retrieval_top_k, 5)

    def test_sql_or_code_fence_repairs_once_and_repeated_invalid_fails(self):
        clean = json.dumps(
            {
                "queries": [
                    "female dysuria clinical guideline",
                    "urinary frequency differential evidence",
                ]
            }
        )
        responses = iter(
            ['{"queries":["```sql SELECT * FROM cases```","x"]}', clean]
        )
        repaired = generate_retrieval_queries(patient(), lambda prompt: next(responses))
        self.assertEqual(len(repaired), 2)

        calls = []
        with self.assertRaises(ValueError):
            generate_retrieval_queries(
                patient(),
                lambda prompt: calls.append(prompt)
                or '{"queries":["SELECT * FROM cases","x"]}',
            )
        self.assertEqual(len(calls), 2)

    def test_merge_deduplicate_and_top_k(self):
        results = {
            "query one": [
                evidence("duplicate", 0.4),
                evidence("one", 0.9),
                evidence("two", 0.8),
                evidence("three", 0.7),
            ],
            "query two": [
                evidence("duplicate", 0.95),
                evidence("four", 0.6),
                evidence("five", 0.5),
                evidence("six", 0.3),
            ],
        }

        def fake_backend(query: str, k: int) -> list[EvidenceChunk]:
            return results[query][:k]

        chunks = retrieve_evidence(["query one", "query two"], fake_backend)

        self.assertEqual(len({chunk.chunk_id for chunk in chunks}), len(chunks))
        duplicate = next(chunk for chunk in chunks if chunk.chunk_id == "duplicate")
        self.assertEqual(duplicate.retrieval_score, 0.95)
        self.assertEqual(duplicate.matched_query, "query two")
        self.assertEqual(len(chunks), DEFAULT_CONFIG.retrieval_top_k)

    def test_empty_retrieval(self):
        self.assertEqual(
            retrieve_evidence(["query one"], lambda query, k: []),
            [],
        )


if __name__ == "__main__":
    unittest.main()
