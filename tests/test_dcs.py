from unittest import TestCase

from core.schemas import DCSDecision
from core.validation.dcs import calculate_dcs


class DCSTests(TestCase):
    def test_formula(self) -> None:
        result = calculate_dcs(kas=0.8, lcs=3)

        self.assertAlmostEqual(result.score, 0.75 * 0.8 + 0.25 * 1.0)

    def test_approved(self) -> None:
        result = calculate_dcs(kas=0.8, lcs=3)

        self.assertEqual(result.decision, DCSDecision.APPROVED)

    def test_follow_up(self) -> None:
        result = calculate_dcs(kas=0.6, lcs=1)

        self.assertEqual(result.decision, DCSDecision.FOLLOW_UP)
