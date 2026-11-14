"""Optional 384-dimension sentence-transformer embeddings for pgvector."""
from __future__ import annotations

import logging
import os
from functools import lru_cache

logger = logging.getLogger(__name__)
EMBEDDING_DIMENSION = 384


@lru_cache(maxsize=1)
def _model():
    model_name = os.getenv("CLAUSEIQ_DENSE_MODEL", "").strip()
    if not model_name:
        return None
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer(model_name)
    except Exception as exc:
        logger.warning("Dense embedding model unavailable (%s); storing lexical-only clauses", type(exc).__name__)
        return None


def embed_texts(texts: list[str]) -> list[list[float]] | None:
    """Return normalized 384-d vectors, or None when dense embeddings are disabled."""
    model = _model()
    if model is None or not texts:
        return None
    try:
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        if vectors.ndim != 2 or vectors.shape[1] != EMBEDDING_DIMENSION:
            raise ValueError(
                f"Configured embedding model must produce {EMBEDDING_DIMENSION} dimensions; "
                f"received {vectors.shape[-1] if vectors.ndim else 'unknown'}."
            )
        return [[float(value) for value in vector] for vector in vectors]
    except Exception as exc:
        logger.warning("Embedding generation skipped (%s)", type(exc).__name__)
        return None
