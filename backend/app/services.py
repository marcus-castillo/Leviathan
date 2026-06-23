"""Service helpers shared by API routes and offline scripts."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.embeddings.encoder import encode
from app.models import Analysis, Opinion
from app.nlp.pipeline import get_pipeline


def analyze_and_store(db: Session, opinion: Opinion, *, with_embedding: bool = True) -> Analysis:
    """Run the NLP pipeline (and optionally embedding) for an opinion and persist the Analysis."""
    pipe = get_pipeline()
    out = pipe.run(opinion.text, case_name=opinion.case_name,
                   citations=(opinion.extra or {}).get("citations", []))

    analysis = db.execute(
        select(Analysis).where(Analysis.opinion_id == opinion.id)
    ).scalar_one_or_none()
    if analysis is None:
        analysis = Analysis(opinion_id=opinion.id)
        db.add(analysis)

    analysis.outcome = out.outcome
    analysis.outcome_confidence = out.outcome_confidence
    analysis.tone_score = out.tone_score
    analysis.party_tone = out.party_tone
    analysis.entities = out.entities
    analysis.issues = out.issues
    analysis.citations = out.citations

    if with_embedding:
        analysis.embedding = encode(opinion.text)

    db.flush()
    return analysis
