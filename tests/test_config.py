import unittest

from core.config import DEFAULT_CONFIG, PipelineConfig


class PipelineConfigTests(unittest.TestCase):
    def test_default_baseline_values(self):
        self.assertEqual(DEFAULT_CONFIG.slm_a_model, "qwen2.5:3b")
        self.assertEqual(DEFAULT_CONFIG.slm_b_model, "gemma2:2b")
        self.assertEqual(DEFAULT_CONFIG.query_count, 3)
        self.assertEqual(DEFAULT_CONFIG.retrieval_top_k, 5)
        self.assertEqual(DEFAULT_CONFIG.chunk_size, 1000)
        self.assertEqual(DEFAULT_CONFIG.chunk_overlap, 200)
        self.assertEqual(DEFAULT_CONFIG.kas_alpha, 0.5)
        self.assertEqual(DEFAULT_CONFIG.dcs_lambda, 0.75)
        self.assertEqual(DEFAULT_CONFIG.dcs_threshold, 0.75)
        self.assertEqual(DEFAULT_CONFIG.max_followup_rounds, 3)

    def test_deterministic_configuration(self):
        self.assertEqual(PipelineConfig(), PipelineConfig())

    def test_invalid_query_count(self):
        with self.assertRaises(ValueError):
            PipelineConfig(query_count=4)

    def test_invalid_chunk_overlap(self):
        with self.assertRaises(ValueError):
            PipelineConfig(chunk_size=1000, chunk_overlap=1000)

    def test_invalid_score_parameter(self):
        with self.assertRaises(ValueError):
            PipelineConfig(dcs_threshold=1.1)


if __name__ == "__main__":
    unittest.main()
