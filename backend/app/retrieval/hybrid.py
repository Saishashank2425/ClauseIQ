"""Hybrid lexical/dense retrieval with reciprocal-rank fusion and optional reranking."""
from __future__ import annotations

import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.app.retrieval.bm25 import BM25Index


class HybridRetriever:
    """Retrieve candidates from independent channels, fuse ranks, then rerank."""

    def __init__(self, documents: list[str]):
        self.documents = documents
        self.bm25 = BM25Index(documents)
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True)
        try:
            self.matrix = self.vectorizer.fit_transform(documents)
        except ValueError:
            self.matrix = None

        self.dense_index = None
        self.dense_model = None
        dense_name = os.getenv("CLAUSEIQ_DENSE_MODEL", "").strip()
        if dense_name and documents:
            try:
                import faiss
                from sentence_transformers import SentenceTransformer
                self.dense_model = SentenceTransformer(dense_name)
                vectors = self.dense_model.encode(
                    documents, normalize_embeddings=True, convert_to_numpy=True
                ).astype("float32")
                self.dense_index = faiss.IndexFlatIP(vectors.shape[1])
                self.dense_index.add(vectors)
            except Exception:
                # Dense retrieval is an optional channel; sparse search remains available.
                self.dense_index = self.dense_model = None

        self.cross_encoder = None
        reranker_name = os.getenv("CLAUSEIQ_CROSS_ENCODER_MODEL", "").strip()
        if reranker_name:
            try:
                from sentence_transformers import CrossEncoder
                self.cross_encoder = CrossEncoder(reranker_name)
            except Exception:
                self.cross_encoder = None

    @staticmethod
    def _ranked_ids(scores: np.ndarray, limit: int) -> list[int]:
        return [int(i) for i in np.argsort(scores)[::-1][:limit] if scores[i] > 0]

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        if not self.documents or not query.strip() or top_k < 1:
            return []
        n = len(self.documents)
        candidate_limit = min(n, max(top_k * 5, 15))
        rrf: dict[int, float] = {}
        rank_constant = 60

        # Each channel contributes rank evidence rather than incomparable raw scores.
        bm25_ranked = self.bm25.search(query, top_k=candidate_limit)
        for rank, (idx, _score) in enumerate(bm25_ranked, start=1):
            rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (rank_constant + rank)

        if self.matrix is not None:
            q = self.vectorizer.transform([query])
            sparse_scores = cosine_similarity(q, self.matrix)[0]
            for rank, idx in enumerate(self._ranked_ids(sparse_scores, candidate_limit), start=1):
                rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (rank_constant + rank)

        if self.dense_index is not None and self.dense_model is not None:
            try:
                vector = self.dense_model.encode(
                    [query], normalize_embeddings=True, convert_to_numpy=True
                ).astype("float32")
                _scores, ids = self.dense_index.search(vector, candidate_limit)
                for rank, idx in enumerate(ids[0], start=1):
                    if idx >= 0:
                        idx = int(idx)
                        rrf[idx] = rrf.get(idx, 0.0) + 1.0 / (rank_constant + rank)
            except Exception:
                pass

        candidates = sorted(rrf.items(), key=lambda pair: pair[1], reverse=True)
        candidates = candidates[:candidate_limit]
        if self.cross_encoder and candidates:
            try:
                pairs = [(query, self.documents[idx]) for idx, _ in candidates]
                logits = np.asarray(self.cross_encoder.predict(pairs), dtype="float32").reshape(-1)
                candidates = [
                    (candidates[j][0], float(logits[j]))
                    for j in range(len(candidates))
                ]
                candidates.sort(key=lambda pair: pair[1], reverse=True)
            except Exception:
                # Preserve the fused ranking if reranking is unavailable.
                pass

        if not candidates:
            return []
        scores = np.asarray([score for _, score in candidates], dtype="float32")
        low, high = float(scores.min()), float(scores.max())
        if high - low > 1e-8:
            normalized = (scores - low) / (high - low)
        else:
            normalized = np.ones_like(scores)
        return [
            (idx, float(normalized[position]))
            for position, (idx, _score) in enumerate(candidates[:top_k])
        ]
