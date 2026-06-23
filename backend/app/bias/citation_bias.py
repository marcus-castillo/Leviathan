"""D. Citation bias: which precedents/authorities a judge cites disproportionately.

Computes the judge's most-cited authorities and contrasts their citation share against the corpus
share (a simple log-ratio "preference" score). Descriptive only.
"""
from __future__ import annotations

import math
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ethics.guardrails import build_caveats
from app.models import Analysis, Opinion
from app.schemas import BiasSignal


def _citation_counts(db: Session, judge_id: int | None) -> Counter:
    stmt = select(Analysis.citations).join(Opinion, Opinion.id == Analysis.opinion_id)
    if judge_id is not None:
        stmt = stmt.where(Opinion.judge_id == judge_id)
    counter: Counter = Counter()
    for cites in db.execute(stmt).scalars().all():
        for c in cites or []:
            counter[c] += 1
    return counter


def citation_preferences(db: Session, judge_id: int, top_k: int = 15) -> list[BiasSignal]:
    judge_counts = _citation_counts(db, judge_id)
    corpus_counts = _citation_counts(db, None)
    judge_total = sum(judge_counts.values())
    corpus_total = sum(corpus_counts.values())
    if judge_total == 0 or corpus_total == 0:
        return []

    preferences = []
    for cite, jc in judge_counts.items():
        j_share = jc / judge_total
        c_share = corpus_counts.get(cite, 0) / corpus_total
        # Smoothed log-ratio: positive => judge cites this more than the corpus.
        log_ratio = math.log((j_share + 1e-6) / (c_share + 1e-6))
        preferences.append((cite, jc, round(j_share, 4), round(c_share, 4), round(log_ratio, 4)))

    preferences.sort(key=lambda x: x[4], reverse=True)
    top = preferences[:top_k]

    return [
        BiasSignal(
            metric="citation.preference_profile",
            description=(
                f"The {len(top)} authorities this judge cites most disproportionately relative to "
                "the corpus (log-ratio > 0 means cited more often than average)."
            ),
            effect_size=top[0][4] if top else 0.0,
            detail={
                "preferences": [
                    {"citation": c, "judge_count": jc, "judge_share": js,
                     "corpus_share": cs, "log_ratio": lr}
                    for c, jc, js, cs, lr in top
                ]
            },
            caveats=build_caveats(
                judge_total,
                base_confidence=0.55,
                extra_limitations=(
                    "Citation preference reflects the mix of legal issues a judge hears; favoring an "
                    "authority is expected when a judge handles many cases in that authority's area."
                ),
                confound_note="docket composition, era, and circuit precedent availability",
            ),
        )
    ]
