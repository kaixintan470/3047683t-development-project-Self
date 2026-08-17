"""Diagnostic Confidence Score quality gate."""

from core.config import DEFAULT_CONFIG
from core.schemas import DCSDecision, DCSResult


def calculate_dcs(kas: float, lcs: int) -> DCSResult:
    """Combine KAS and normalised LCS using the configured quality gate."""
    normalised_lcs = lcs / 3
    score = (
        DEFAULT_CONFIG.dcs_lambda * kas
        + (1 - DEFAULT_CONFIG.dcs_lambda) * normalised_lcs
    )
    decision = (
        DCSDecision.APPROVED
        if score >= DEFAULT_CONFIG.dcs_threshold
        else DCSDecision.FOLLOW_UP
    )
    return DCSResult(score=score, decision=decision)
