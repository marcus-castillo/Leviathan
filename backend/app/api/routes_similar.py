"""/similar-cases — embedding retrieval + cross-judge outcome comparison on like fact patterns."""
from __future__ import annotations

from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.embeddings.encoder import encode
from app.embeddings.similar import find_similar
from app.ethics.guardrails import GLOBAL_DISCLAIMER, build_caveats
from app.models import Opinion
from app.schemas import BiasSignal, SimilarCase, SimilarCasesIn, SimilarCasesResult

router = APIRouter(tags=["similar"])


@router.post("/similar-cases", response_model=SimilarCasesResult)
def similar_cases(payload: SimilarCasesIn, db: Session = Depends(get_db)) -> SimilarCasesResult:
    query_vector = None
    query_summary = ""

    if payload.opinion_id is not None:
        op = db.get(Opinion, payload.opinion_id)
        if op is None or op.analysis is None or op.analysis.embedding is None:
            raise HTTPException(404, "Opinion not found or not yet embedded.")
        query_vector = list(op.analysis.embedding)
        query_summary = f"Cases similar to: {op.case_name}"
    elif payload.text:
        query_vector = encode(payload.text)
        query_summary = "Cases similar to the supplied text."
    else:
        raise HTTPException(422, "Provide either text or opinion_id.")

    raw = find_similar(
        db,
        query_vector=query_vector,
        exclude_opinion_id=payload.opinion_id,
        case_type=payload.case_type,
        top_k=payload.top_k,
    )
    results = [SimilarCase(**r) for r in raw]

    # Cross-judge outcome comparison over the retrieved like-fact set.
    comparison = None
    outcomes = [r["outcome"] for r in raw if r["outcome"] in ("plaintiff", "defendant")]
    if len(outcomes) >= 2:
        counts = Counter(outcomes)
        p = counts.get("plaintiff", 0)
        n = len(outcomes)
        by_judge = Counter(
            r["judge"] for r in raw if r["judge"] and r["outcome"] in ("plaintiff", "defendant")
        )
        comparison = BiasSignal(
            metric="similar.outcome_consistency",
            description=(
                f"Among {n} retrieved like-fact opinions, {p/n:.0%} favored the plaintiff/appellant. "
                f"Spread across {len(by_judge)} judge(s)."
            ),
            effect_size=round(p / n - 0.5, 4),
            detail={"outcome_counts": dict(counts), "by_judge": dict(by_judge)},
            caveats=build_caveats(
                n,
                base_confidence=0.45,
                extra_limitations=(
                    "Embedding similarity captures textual/topical resemblance, NOT legal "
                    "equivalence; 'similar' cases may differ on facts that legitimately change the "
                    "outcome. Do not read divergent outcomes here as inconsistency by any judge."
                ),
                confound_note="latent factual differences and procedural posture",
            ),
        )

    return SimilarCasesResult(
        query_summary=query_summary,
        results=results,
        outcome_comparison=comparison,
        disclaimer=GLOBAL_DISCLAIMER,
    )
