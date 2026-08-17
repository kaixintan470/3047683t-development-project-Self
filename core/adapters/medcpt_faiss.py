"""MedCPT document/query embeddings backed by a local FAISS index."""

from dataclasses import asdict
import json
from pathlib import Path

import faiss
import numpy as np
import torch
from transformers import AutoModel, AutoTokenizer

from core.corpus import GUIDELINE_MANIFEST, preprocess_document
from core.schemas import EvidenceChunk


QUERY_MODEL = "ncbi/MedCPT-Query-Encoder"
ARTICLE_MODEL = "ncbi/MedCPT-Article-Encoder"
MODEL_CACHE = Path("models/huggingface")


class MedCPTFAISS:
    def __init__(self, corpus_dir: str | Path, index_dir: str | Path) -> None:
        self.corpus_dir = Path(corpus_dir)
        self.index_dir = Path(index_dir)
        self.index_path = self.index_dir / "medcpt.index"
        self.metadata_path = self.index_dir / "medcpt_metadata.json"
        self._query_tokenizer = None
        self._query_model = None
        self._article_tokenizer = None
        self._article_model = None
        self._index = None
        self._chunks: list[EvidenceChunk] = []

    def _load_query_encoder(self) -> None:
        if self._query_model is None:
            self._query_tokenizer = AutoTokenizer.from_pretrained(
                QUERY_MODEL, cache_dir=MODEL_CACHE
            )
            self._query_model = AutoModel.from_pretrained(
                QUERY_MODEL, cache_dir=MODEL_CACHE
            )
            self._query_model.eval()

    def _load_article_encoder(self) -> None:
        if self._article_model is None:
            self._article_tokenizer = AutoTokenizer.from_pretrained(
                ARTICLE_MODEL, cache_dir=MODEL_CACHE
            )
            self._article_model = AutoModel.from_pretrained(
                ARTICLE_MODEL, cache_dir=MODEL_CACHE
            )
            self._article_model.eval()

    @staticmethod
    def _normalise(vectors: np.ndarray) -> np.ndarray:
        vectors = np.ascontiguousarray(vectors.astype("float32"))
        faiss.normalize_L2(vectors)
        return vectors

    def embed_queries(self, texts: list[str]) -> np.ndarray:
        self._load_query_encoder()
        encoded = self._query_tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=64,
            return_tensors="pt",
        )
        with torch.inference_mode():
            vectors = self._query_model(**encoded).last_hidden_state[:, 0, :]
        return self._normalise(vectors.cpu().numpy())

    def embed_articles(self, chunks: list[EvidenceChunk], batch_size: int = 8) -> np.ndarray:
        self._load_article_encoder()
        batches: list[np.ndarray] = []
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            encoded = self._article_tokenizer(
                [chunk.title for chunk in batch],
                [chunk.content for chunk in batch],
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            with torch.inference_mode():
                vectors = self._article_model(**encoded).last_hidden_state[:, 0, :]
            batches.append(vectors.cpu().numpy())
        return self._normalise(np.concatenate(batches, axis=0))

    def _preprocess_corpus(self) -> list[EvidenceChunk]:
        pdfs = sorted(self.corpus_dir.glob("*.pdf"))
        if len(pdfs) != len(GUIDELINE_MANIFEST):
            raise RuntimeError("controlled guideline corpus must contain 10 PDFs")

        chunks: list[EvidenceChunk] = []
        for path, entry in zip(pdfs, GUIDELINE_MANIFEST, strict=True):
            chunks.extend(
                preprocess_document(
                    path,
                    source=entry.organisation,
                    title=f"{entry.title} ({entry.year})",
                )
            )
        return chunks

    def build(self) -> None:
        chunks = self._preprocess_corpus()
        vectors = self.embed_articles(chunks)
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)

        self.index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(self.index_path))
        self.metadata_path.write_text(
            json.dumps([asdict(chunk) for chunk in chunks], ensure_ascii=False),
            encoding="utf-8",
        )
        self._index = index
        self._chunks = chunks

    def load(self) -> None:
        if not self.index_path.exists() or not self.metadata_path.exists():
            self.build()
            return
        self._index = faiss.read_index(str(self.index_path))
        payload = json.loads(self.metadata_path.read_text(encoding="utf-8"))
        self._chunks = [EvidenceChunk(**item) for item in payload]

    def search(self, query: str, top_k: int) -> list[EvidenceChunk]:
        if self._index is None:
            self.load()
        scores, indexes = self._index.search(self.embed_queries([query]), top_k)
        results: list[EvidenceChunk] = []
        for score, index in zip(scores[0], indexes[0], strict=True):
            if index < 0:
                continue
            payload = asdict(self._chunks[int(index)])
            payload["retrieval_score"] = float(score)
            results.append(EvidenceChunk(**payload))
        return results

    def semantic_similarity(
        self,
        claim: str,
        evidence: list[EvidenceChunk],
    ) -> float:
        if not evidence:
            return 0.0
        query = self.embed_queries([claim])
        articles = self.embed_articles(evidence)
        cosine = float(np.max(query @ articles.T))
        return (cosine + 1.0) / 2.0
