"""Sentence-transformer encoder (singleton)."""
from __future__ import annotations

from functools import lru_cache

from app.config import settings


@lru_cache
def get_encoder():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(settings.embedding_model)


def encode(text: str) -> list[float]:
    vec = get_encoder().encode(text[:50_000], normalize_embeddings=True)
    return vec.tolist()


def encode_batch(texts: list[str], batch_size: int = 32) -> list[list[float]]:
    vecs = get_encoder().encode(
        [t[:50_000] for t in texts],
        normalize_embeddings=True,
        batch_size=batch_size,
        show_progress_bar=False,
    )
    return [v.tolist() for v in vecs]
