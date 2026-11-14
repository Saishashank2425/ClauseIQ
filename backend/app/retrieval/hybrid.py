"""Sparse + optional dense retrieval, with optional cross-encoder reranking."""
from __future__ import annotations
import os
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.retrieval.bm25 import BM25Index

class HybridRetriever:
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
        dense_name = os.getenv("CLAUSEIQ_DENSE_MODEL")
        if dense_name and documents:
            try:
                import faiss
                from sentence_transformers import SentenceTransformer
                self.dense_model = SentenceTransformer(dense_name)
                vectors = self.dense_model.encode(documents, normalize_embeddings=True, convert_to_numpy=True).astype("float32")
                self.dense_index = faiss.IndexFlatIP(vectors.shape[1])
                self.dense_index.add(vectors)
            except Exception:
                self.dense_index = self.dense_model = None
        self.cross_encoder = None
        reranker_name = os.getenv("CLAUSEIQ_CROSS_ENCODER_MODEL")
        if reranker_name:
            try:
                from sentence_transformers import CrossEncoder
                self.cross_encoder = CrossEncoder(reranker_name)
            except Exception:
                self.cross_encoder = None

    def search(self, query: str, top_k: int = 5) -> list[tuple[int, float]]:
        if not self.documents or not query.strip():
            return []
        n = len(self.documents)
        scores = np.zeros(n, dtype="float32")
        bm = self.bm25.search(query, top_k=n)
        if bm:
            maximum = max(score for _, score in bm) or 1.0
            for index, score in bm:
                scores[index] += 0.45 * score / maximum
        if self.matrix is not None:
            q = self.vectorizer.transform([query])
            sparse = cosine_similarity(q, self.matrix)[0]
            scores += 0.35 * sparse.astype("float32")
        if self.dense_index is not None and self.dense_model is not None:
            try:
                vector = self.dense_model.encode([query], normalize_embeddings=True, convert_to_numpy=True).astype("float32")
                dense_scores, dense_ids = self.dense_index.search(vector, min(n, max(top_k * 4, top_k)))
                for idx, score in zip(dense_ids[0], dense_scores[0]):
                    if idx >= 0:
                        scores[int(idx)] += 0.20 * max(0.0, float(score))
            except Exception:
                pass
        candidates = [(i, float(score)) for i, score in enumerate(scores) if score > 0]
        candidates.sort(key=lambda pair: pair[1], reverse=True)
        candidates = candidates[:max(top_k * 3, top_k)]
        if self.cross_encoder and candidates:
            try:
                pairs = [(query, self.documents[i]) for i, _ in candidates]
                logits = np.asarray(self.cross_encoder.predict(pairs), dtype="float32").reshape(-1)
                probs = 1.0 / (1.0 + np.exp(-np.clip(logits, -30, 30)))
                candidates = [(candidates[j][0], float(probs[j])) for j in range(len(candidates))]
                candidates.sort(key=lambda pair: pair[1], reverse=True)
            except Exception:
                pass
        if not candidates:
            return []
        maximum = candidates[0][1] or 1.0
        return [(idx, score / maximum) for idx, score in candidates[:top_k]]
