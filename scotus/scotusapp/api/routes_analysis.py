"""/analysis/* — majority-vs-dissent divergence, topics, temporal evolution."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from scotusapp.analysis import tag_themes, topic_model, weighted_log_odds
from scotusapp.config import settings
from scotusapp.db import Case, OpinionSegment, get_db
from scotusapp.ethics import GLOBAL_DISCLAIMER
from scotusapp.schemas import DivergenceResult, EvolutionResult, TopicsResult

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/divergence", response_model=DivergenceResult)
def divergence(case_id: int = Query(...), db: Session = Depends(get_db)) -> DivergenceResult:
    case = db.get(Case, case_id)
    if case is None:
        raise HTTPException(404, "Case not found")

    majority = [s.text for s in case.segments if s.kind == "majority"]
    dissent = [s.text for s in case.segments if s.kind in ("dissent", "mixed")]
    if not majority or not dissent:
        return DivergenceResult(
            case_id=case_id, case_name=case.name, majority_terms=[], dissent_terms=[],
            note="Case lacks both a majority and a dissent to contrast.",
            disclaimer=GLOBAL_DISCLAIMER,
        )

    res = weighted_log_odds(majority, dissent, top_k=settings.lexical_top_k)
    return DivergenceResult(
        case_id=case_id, case_name=case.name,
        majority_terms=res["a"], dissent_terms=[(w, abs(z)) for w, z in res["b"]],
        disclaimer=GLOBAL_DISCLAIMER,
    )


@router.get("/topics", response_model=TopicsResult)
def topics(db: Session = Depends(get_db)) -> TopicsResult:
    rows = db.execute(select(OpinionSegment.text).where(OpinionSegment.kind == "majority")).scalars().all()
    model = topic_model(list(rows), n_topics=settings.n_topics)

    theme_counts: Counter = Counter()
    for text in rows:
        for theme in tag_themes(text):
            theme_counts[theme] += 1

    return TopicsResult(
        topics=model.get("topics", []),
        theme_distribution=dict(theme_counts),
        disclaimer=GLOBAL_DISCLAIMER,
    )


@router.get("/evolution", response_model=EvolutionResult)
def evolution(db: Session = Depends(get_db)) -> EvolutionResult:
    """Theme mix per SCOTUS term — how topical emphasis shifts over time."""
    rows = db.execute(
        select(Case.term, OpinionSegment.text)
        .join(OpinionSegment, OpinionSegment.case_id == Case.id)
        .where(OpinionSegment.kind == "majority", Case.term.isnot(None))
    ).all()

    by_term: dict[int, Counter] = {}
    for term, text in rows:
        bucket = by_term.setdefault(int(term), Counter())
        for theme in tag_themes(text):
            bucket[theme] += 1

    series = [
        {"term": term, "themes": dict(counts), "total": sum(counts.values())}
        for term, counts in sorted(by_term.items())
    ]
    return EvolutionResult(by_term=series, disclaimer=GLOBAL_DISCLAIMER)
