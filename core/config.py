"""Central engineering configuration for the clinical reasoning pipeline."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PipelineConfig:
    model_runtime: str = "ollama"

    slm_a_model: str = "qwen2.5:3b"
    slm_b_model: str = "gemma2:2b"

    model_temperature: float = 0.0

    retrieval_embedding: str = "MedCPT"
    vector_index: str = "FAISS"

    query_count: int = 3
    retrieval_top_k: int = 5

    chunk_size: int = 1000
    chunk_overlap: int = 200

    kas_alpha: float = 0.5

    dcs_lambda: float = 0.75
    dcs_threshold: float = 0.75

    max_followup_rounds: int = 3

    def __post_init__(self) -> None:
        if not self.model_runtime:
            raise ValueError("model_runtime must not be empty")
        if not self.slm_a_model:
            raise ValueError("slm_a_model must not be empty")
        if not self.slm_b_model:
            raise ValueError("slm_b_model must not be empty")
        if self.model_temperature < 0:
            raise ValueError("model_temperature must be non-negative")
        if self.query_count not in (2, 3):
            raise ValueError("query_count must be 2 or 3")
        if self.retrieval_top_k <= 0:
            raise ValueError("retrieval_top_k must be positive")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        if not 0 <= self.kas_alpha <= 1:
            raise ValueError("kas_alpha must be between 0 and 1")
        if not 0 <= self.dcs_lambda <= 1:
            raise ValueError("dcs_lambda must be between 0 and 1")
        if not 0 <= self.dcs_threshold <= 1:
            raise ValueError("dcs_threshold must be between 0 and 1")
        if self.max_followup_rounds < 1:
            raise ValueError("max_followup_rounds must be at least 1")


DEFAULT_CONFIG = PipelineConfig()
