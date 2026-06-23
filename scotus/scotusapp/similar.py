"""Similar-case finder — surfaces cases with similar reasoning, flagging cross-divide matches.

Similarity is over majority-opinion embeddings (the Court's reasoning). A match is flagged
``crosses_divide`` when the similar case's majority author falls in a different *style cluster* than
the query's majority author — i.e. similar reasoning written from a stylistically different chair.
This is a stylistic, not ideological, signal (see ethics).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from scotusapp.db import Case, OpinionSegment


def _majority_segment(db: Session, case_id: int) -> OpinionSegment | None:
    return db.execute(
        select(OpinionSegment).where(
            OpinionSegment.case_id == case_id, OpinionSegment.kind == "majority"
        )
    ).scalars().first()


def find_similar_cases(
    db: Session,
    *,
    query_vector: list[float],
    exclude_case_id: int | None = None,
    style_cluster_of: dict[str, int] | None = None,
    query_author: str | None = None,
    top_k: int = 10,
) -> list[dict]:
    distance = OpinionSegment.embedding.cosine_distance(query_vector).label("distance")
    stmt = (
        select(OpinionSegment.case_id, OpinionSegment.author_name, Case.name, Case.term, distance)
        .join(Case, Case.id == OpinionSegment.case_id)
        .where(OpinionSegment.kind == "majority", OpinionSegment.embedding.isnot(None))
        .order_by(distance)
        .limit(top_k + (1 if exclude_case_id else 0))
    )
    if exclude_case_id:
        stmt = stmt.where(OpinionSegment.case_id != exclude_case_id)

    style_cluster_of = style_cluster_of or {}
    q_cluster = style_cluster_of.get(query_author) if query_author else None

    results = []
    for row in db.execute(stmt).all()[:top_k]:
        author = row.author_name
        other_cluster = style_cluster_of.get(author)
        crosses = (
            q_cluster is not None and other_cluster is not None and q_cluster != other_cluster
        )
        results.append({
            "case_id": row.case_id,
            "case_name": row.name,
            "term": row.term,
            "majority_author": author,
            "similarity": round(1.0 - float(row.distance), 4),
            "crosses_divide": crosses,
        })
    return results
