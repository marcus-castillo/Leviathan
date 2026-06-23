"""Per-case sentence-transformer embeddings (case-similarity vectors).

Thin wrapper over the backend encoder so corpus vectors share the backend's 384-dim MiniLM space and
are directly comparable to the live API's embeddings.
"""
from __future__ import annotations

from levcorpus.config import EMBEDDING_MODEL


def embedding_model_name() -> str:
    return EMBEDDING_MODEL


def embed_text(text: str) -> list[float]:
    from app.embeddings.encoder import encode  # backend reuse

    return encode(text)
