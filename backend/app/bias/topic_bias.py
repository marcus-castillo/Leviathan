"""C. Topic bias: differences in outcomes across case categories for a judge.

Compares this judge's plaintiff-favoring rate within each case type against the judge's own overall
rate, flagging categories where the within-category rate diverges most. (Comparison against a court-
or corpus-wide baseline is also supported via ``baseline_rates``.)
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bias.stats import benjamini_hochberg, two_proportion_ztest
from app.ethics.guardrails import build_caveats
from app.models import Analysis, Opinion
from app.schemas import BiasSignal


def topic_bias(
    db: Session,
    judge_id: int,
    baseline_rates: dict[str, tuple[int, int]] | None = None,
) -> list[BiasSignal]:
    rows = db.execute(
        select(Opinion.case_type, Analysis.outcome)
        .join(Analysis, Analysis.opinion_id == Opinion.id)
        .where(Opinion.judge_id == judge_id)
    ).all()

    by_type: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        if r.case_type and r.outcome in ("plaintiff", "defendant"):
            by_type[r.case_type].append(r.outcome)

    overall_p = sum(1 for v in by_type.values() for o in v if o == "plaintiff")
    overall_n = sum(len(v) for v in by_type.values())
    if overall_n == 0:
        return []

    signals: list[BiasSignal] = []
    pending: list[tuple[BiasSignal, float]] = []
    for ctype, outcomes in by_type.items():
        n = len(outcomes)
        p = sum(o == "plaintiff" for o in outcomes)
        if baseline_rates and ctype in baseline_rates:
            b_p, b_n = baseline_rates[ctype]
            comparison = "the corpus baseline for this case type"
        else:
            # Compare category rate against this judge's own all-category rate.
            b_p, b_n = overall_p, overall_n
            comparison = "this judge's overall rate across case types"

        test = two_proportion_ztest(p, n, b_p, b_n)
        sig = BiasSignal(
            metric=f"topic.{ctype}",
            description=(
                f"In {ctype} matters the plaintiff-favoring rate was {test.rate_a:.0%} "
                f"(n={n}) vs {test.rate_b:.0%} for {comparison}."
            ),
            effect_size=test.diff,
            p_value=test.p_value,
            detail={"case_type": ctype, "plaintiff": p, "n": n,
                    "baseline_rate": test.rate_b, "comparison": comparison},
            caveats=build_caveats(
                n,
                base_confidence=0.5,
                confound_note="case-type-specific law, fact patterns, and selection effects",
            ),
        )
        pending.append((sig, test.p_value))

    # Multiple-comparison correction across case types.
    q = benjamini_hochberg([p for _, p in pending], alpha=0.05)
    for (sig, _), qv in zip(pending, q):
        sig.p_value_adjusted = qv
        signals.append(sig)

    signals.sort(key=lambda s: abs(s.effect_size or 0), reverse=True)
    return signals
