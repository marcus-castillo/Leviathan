"""/analyze-case — run the full NLP pipeline on a single opinion (optionally persisting it)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.ethics.guardrails import GLOBAL_DISCLAIMER
from app.ingestion.base import upsert_opinion
from app.nlp.pipeline import get_pipeline
from app.schemas import AnalyzeResult, Entity, OpinionIn
from app.services import analyze_and_store

router = APIRouter(tags=["cases"])


@router.post("/analyze-case", response_model=AnalyzeResult)
def analyze_case(
    payload: OpinionIn,
    persist: bool = Query(False, description="Store the opinion + analysis for later aggregation."),
    db: Session = Depends(get_db),
) -> AnalyzeResult:
    if persist:
        opinion = upsert_opinion(
            db,
            case_name=payload.case_name,
            text=payload.text,
            judge_name=payload.judge_name,
            court=payload.court,
            decided=payload.decided,
            case_type=payload.case_type,
            citations=payload.citations,
            source=payload.source,
            external_id=payload.external_id,
        )
        analysis = analyze_and_store(db, opinion)
        db.commit()
        out = type("O", (), {
            "outcome": analysis.outcome, "outcome_confidence": analysis.outcome_confidence,
            "tone_score": analysis.tone_score, "party_tone": analysis.party_tone,
            "entities": analysis.entities, "issues": analysis.issues,
            "citations": analysis.citations,
        })
    else:
        out = get_pipeline().run(payload.text, case_name=payload.case_name,
                                 citations=payload.citations)

    entities = [
        Entity(text=t, label=label)
        for label, items in out.entities.items()
        for t in items
    ]
    return AnalyzeResult(
        case_name=payload.case_name,
        outcome=out.outcome,
        outcome_confidence=out.outcome_confidence,
        tone_score=out.tone_score,
        party_tone=out.party_tone,
        entities=entities,
        issues=out.issues,
        citations=out.citations,
        disclaimer=GLOBAL_DISCLAIMER,
    )
