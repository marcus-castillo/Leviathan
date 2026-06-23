"""/judge-profile and /compare-judges — aggregated disparity signals with mandatory caveats."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.bias import (
    citation_preferences,
    outcome_disparity,
    sentiment_bias,
    topic_bias,
)
from app.bias.explain import explain_all
from app.bias.stats import two_proportion_ztest
from app.config import settings
from app.db import get_db
from app.ethics.guardrails import GLOBAL_DISCLAIMER, build_caveats
from app.models import Analysis, Judge, Opinion
from app.schemas import (
    BiasSignal,
    CompareJudgesIn,
    CompareJudgesResult,
    JudgeProfile,
)

router = APIRouter(tags=["judges"])


def _n_opinions(db: Session, judge_id: int) -> int:
    return db.execute(
        select(func.count(Opinion.id)).where(Opinion.judge_id == judge_id)
    ).scalar_one()


def _build_profile(db: Session, judge: Judge, case_type: str | None) -> JudgeProfile:
    n = _n_opinions(db, judge.id)
    signals: list[BiasSignal] = []
    if n >= 1:
        signals += outcome_disparity(db, judge.id, case_type)
        signals += sentiment_bias(db, judge.id, case_type)
        signals += topic_bias(db, judge.id)
        signals += citation_preferences(db, judge.id)

    disclaimer = GLOBAL_DISCLAIMER
    if n < settings.min_sample_size:
        disclaimer = (
            f"⚠️ This judge has only n={n} analyzed opinions, below the reliable minimum "
            f"(n={settings.min_sample_size}). Figures are shown for transparency only. " + disclaimer
        )
    return JudgeProfile(
        judge_id=judge.id,
        display_name=judge.display_name,
        n_opinions=n,
        signals=signals,
        disclaimer=disclaimer,
    )


@router.get("/judge-profile/{judge_id}", response_model=JudgeProfile)
def judge_profile(
    judge_id: int,
    case_type: str | None = Query(None),
    db: Session = Depends(get_db),
) -> JudgeProfile:
    judge = db.get(Judge, judge_id)
    if judge is None:
        raise HTTPException(404, "Judge not found")
    return _build_profile(db, judge, case_type)


@router.get("/judge-profile/{judge_id}/explain")
def judge_profile_explain(
    judge_id: int,
    case_type: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:
    """Same signals, expanded into plain-language explanations (explainability layer)."""
    judge = db.get(Judge, judge_id)
    if judge is None:
        raise HTTPException(404, "Judge not found")
    profile = _build_profile(db, judge, case_type)
    return {
        "judge_id": judge_id,
        "display_name": judge.display_name,
        "n_opinions": profile.n_opinions,
        "explanations": explain_all(profile.signals),
        "disclaimer": profile.disclaimer,
    }


@router.post("/compare-judges", response_model=CompareJudgesResult)
def compare_judges(payload: CompareJudgesIn, db: Session = Depends(get_db)) -> CompareJudgesResult:
    judges = [db.get(Judge, jid) for jid in payload.judge_ids]
    if any(j is None for j in judges):
        raise HTTPException(404, "One or more judges not found")

    profiles = [_build_profile(db, j, payload.case_type) for j in judges]

    # Cross-judge signal: pairwise plaintiff-rate comparison for the first two judges.
    cross: list[BiasSignal] = []
    rates = []
    for j in judges:
        rows = db.execute(
            select(Analysis.outcome)
            .join(Opinion, Opinion.id == Analysis.opinion_id)
            .where(Opinion.judge_id == j.id)
        ).scalars().all()
        p = sum(o == "plaintiff" for o in rows)
        d = sum(o == "defendant" for o in rows)
        rates.append((j, p, p + d))

    for i in range(len(rates)):
        for k in range(i + 1, len(rates)):
            (ja, pa, na), (jb, pb, nb) = rates[i], rates[k]
            if na == 0 or nb == 0:
                continue
            test = two_proportion_ztest(pa, na, pb, nb)
            cross.append(
                BiasSignal(
                    metric="compare.plaintiff_rate",
                    description=(
                        f"{ja.display_name}: {test.rate_a:.0%} plaintiff-favoring (n={na}) vs "
                        f"{jb.display_name}: {test.rate_b:.0%} (n={nb}); difference {test.diff:+.0%}."
                    ),
                    effect_size=test.diff,
                    p_value=test.p_value,
                    detail={"judge_a": ja.display_name, "judge_b": jb.display_name,
                            "n_a": na, "n_b": nb},
                    caveats=build_caveats(
                        min(na, nb),
                        base_confidence=0.5,
                        extra_limitations=(
                            "Different judges hear different dockets; rate differences need not "
                            "reflect anything about how either judge decides like cases."
                        ),
                        confound_note="docket assignment, case mix, and time period",
                    ),
                )
            )

    return CompareJudgesResult(
        judges=profiles,
        cross_judge_signals=cross,
        disclaimer=GLOBAL_DISCLAIMER,
    )
