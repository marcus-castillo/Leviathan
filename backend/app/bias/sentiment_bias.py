"""B. Language tone bias: differences in ruling-language tone across party roles.

Framed strictly as tone of *language*, not feeling toward a person.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bias.stats import cohens_d, mann_whitney
from app.ethics.guardrails import build_caveats
from app.models import Analysis, Opinion
from app.schemas import BiasSignal


def sentiment_bias(db: Session, judge_id: int, case_type: str | None = None) -> list[BiasSignal]:
    stmt = (
        select(Analysis.party_tone)
        .join(Opinion, Opinion.id == Analysis.opinion_id)
        .where(Opinion.judge_id == judge_id)
    )
    if case_type:
        stmt = stmt.where(Opinion.case_type == case_type)
    rows = db.execute(stmt).scalars().all()

    gov_scores: list[float] = []
    priv_scores: list[float] = []
    for pt in rows:
        if not pt:
            continue
        if "government" in pt:
            gov_scores.append(float(pt["government"]))
        if "private" in pt:
            priv_scores.append(float(pt["private"]))

    if len(gov_scores) < 2 or len(priv_scores) < 2:
        return []

    effect, p = mann_whitney(gov_scores, priv_scores)
    d = cohens_d(gov_scores, priv_scores)
    mean_gov = round(sum(gov_scores) / len(gov_scores), 4)
    mean_priv = round(sum(priv_scores) / len(priv_scores), 4)

    return [
        BiasSignal(
            metric="tone.government_vs_private",
            description=(
                f"Ruling-language tone in sentences referencing government parties averaged "
                f"{mean_gov:+.3f} vs {mean_priv:+.3f} for private parties "
                f"(higher = more approving register)."
            ),
            effect_size=d,
            p_value=p,
            detail={
                "mean_tone_government": mean_gov,
                "mean_tone_private": mean_priv,
                "rank_biserial": effect,
                "n_government": len(gov_scores),
                "n_private": len(priv_scores),
            },
            caveats=build_caveats(
                min(len(gov_scores), len(priv_scores)),
                base_confidence=0.5,
                extra_limitations=(
                    "Tone is a lexical property of the opinion text and may reflect the strength of "
                    "the legal arguments or the record rather than disposition toward any party."
                ),
                confound_note="argument strength, area of law, and opinion length",
            ),
        )
    ]
