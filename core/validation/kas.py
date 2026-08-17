"""Claim-level Knowledge Alignment Score calculation."""

from collections.abc import Callable
from math import exp

from core.config import DEFAULT_CONFIG
from core.schemas import EvidenceChunk, KASResult


SemanticSimilarity = Callable[[str, list[EvidenceChunk]], float]
EvidenceRelation = Callable[[str, list[EvidenceChunk]], float]
ClaimContribution = Callable[[str], float]


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + exp(-value))


def calculate_kas(
    claims: list[str],
    evidence: list[EvidenceChunk],
    semantic_similarity: SemanticSimilarity,
    evidence_relation: EvidenceRelation,
    claim_contribution: ClaimContribution,
) -> KASResult:
    alpha = DEFAULT_CONFIG.kas_alpha
    weighted_sum = 0.0

    for claim in claims:
        similarity = semantic_similarity(claim, evidence)
        evidence_probability = evidence_relation(claim, evidence)
        tms = alpha * similarity + (1 - alpha) * evidence_probability
        weighted_sum += claim_contribution(claim) * tms

    score = _sigmoid(weighted_sum)
    return KASResult(
        score=score,
        rationale=(
            f"Claim-level evidence support used alpha={alpha} across "
            f"{len(claims)} claim(s)."
        ),
    )
