"""Shared services: segment embedding + justice fingerprint construction (reuses backend encoder)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from scotusapp.analysis.justice_embeddings import mean_pool
from scotusapp.db import Justice, OpinionSegment


def _encode(text: str) -> list[float]:
    from app.embeddings.encoder import encode  # backend reuse

    return encode(text)


def embed_segments(db: Session, *, only_missing: bool = True, limit: int | None = None) -> int:
    stmt = select(OpinionSegment)
    if only_missing:
        stmt = stmt.where(OpinionSegment.embedding.is_(None))
    if limit:
        stmt = stmt.limit(limit)
    segments = db.execute(stmt).scalars().all()
    for i, seg in enumerate(segments, 1):
        seg.embedding = _encode(seg.text)
        if i % 20 == 0:
            db.commit()
    db.commit()
    return len(segments)


def build_justice_fingerprints(db: Session) -> int:
    """Mean-pool each justice's authored-segment embeddings into a style fingerprint."""
    justices = db.execute(select(Justice)).scalars().all()
    n = 0
    for justice in justices:
        vecs = [s.embedding for s in justice.segments if s.embedding is not None]
        pooled = mean_pool([list(v) for v in vecs])
        justice.embedding = pooled
        justice.n_segments = len(vecs)
        if pooled is not None:
            n += 1
    db.commit()
    return n
