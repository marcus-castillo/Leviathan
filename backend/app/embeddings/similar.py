"""Embedding-based similar-case retrieval using pgvector cosine distance."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings.encoder import encode
from app.models import Analysis, Court, Judge, Opinion


def find_similar(
    db: Session,
    *,
    query_text: str | None = None,
    query_vector: list[float] | None = None,
    exclude_opinion_id: int | None = None,
    case_type: str | None = None,
    top_k: int = 10,
) -> list[dict]:
    """Return the top-k most similar analyzed opinions with metadata and cosine similarity.

    Embeddings are normalized, so cosine_distance d gives similarity = 1 - d.
    """
    if query_vector is None:
        if not query_text:
            raise ValueError("Provide query_text or query_vector.")
        query_vector = encode(query_text)

    distance = Analysis.embedding.cosine_distance(query_vector).label("distance")
    stmt = (
        select(
            Opinion.id,
            Opinion.case_name,
            Opinion.case_type,
            Analysis.outcome,
            Judge.display_name.label("judge"),
            Court.name.label("court"),
            distance,
        )
        .join(Analysis, Analysis.opinion_id == Opinion.id)
        .outerjoin(Judge, Judge.id == Opinion.judge_id)
        .outerjoin(Court, Court.id == Opinion.court_id)
        .where(Analysis.embedding.isnot(None))
        .order_by(distance)
        .limit(top_k + (1 if exclude_opinion_id else 0))
    )
    if case_type:
        stmt = stmt.where(Opinion.case_type == case_type)
    if exclude_opinion_id:
        stmt = stmt.where(Opinion.id != exclude_opinion_id)

    rows = db.execute(stmt).all()
    results = []
    for r in rows[:top_k]:
        results.append(
            {
                "opinion_id": r.id,
                "case_name": r.case_name,
                "judge": r.judge,
                "court": r.court,
                "outcome": r.outcome,
                "case_type": r.case_type,
                "similarity": round(1.0 - float(r.distance), 4),
            }
        )
    return results
