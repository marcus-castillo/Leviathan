"""A. Outcome disparity: win rates by judge and by party type (government vs private)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.bias.stats import two_proportion_ztest
from app.ethics.guardrails import build_caveats
from app.models import Analysis, Opinion
from app.nlp.pipeline import classify_party_role
from app.schemas import BiasSignal


def _judge_rows(db: Session, judge_id: int, case_type: str | None):
    stmt = (
        select(Opinion.id, Analysis.outcome, Analysis.entities, Opinion.case_type)
        .join(Analysis, Analysis.opinion_id == Opinion.id)
        .where(Opinion.judge_id == judge_id)
    )
    if case_type:
        stmt = stmt.where(Opinion.case_type == case_type)
    return db.execute(stmt).all()


def outcome_disparity(db: Session, judge_id: int, case_type: str | None = None) -> list[BiasSignal]:
    """Compute outcome-rate signals for one judge.

    Signal 1: plaintiff vs defendant win rate (descriptive, with caveats).
    Signal 2: government-party vs private-party prevailing rate, when party roles are inferable.
    """
    rows = _judge_rows(db, judge_id, case_type)
    n = len(rows)
    signals: list[BiasSignal] = []

    # --- Signal 1: plaintiff vs defendant disposition mix ---
    plaintiff = sum(r.outcome == "plaintiff" for r in rows)
    defendant = sum(r.outcome == "defendant" for r in rows)
    decided = plaintiff + defendant
    if decided > 0:
        test = two_proportion_ztest(plaintiff, decided, defendant, decided)
        signals.append(
            BiasSignal(
                metric="outcome.plaintiff_vs_defendant",
                description=(
                    f"Of {decided} clearly-decided opinions, {test.rate_a:.0%} favored the "
                    f"plaintiff/appellant and {1 - test.rate_a:.0%} the defendant/appellee."
                ),
                effect_size=round(plaintiff / decided - 0.5, 4),
                p_value=test.p_value,
                detail={"plaintiff": plaintiff, "defendant": defendant, "decided": decided,
                        "undecided_or_mixed": n - decided},
                caveats=build_caveats(decided, base_confidence=0.6,
                                      confound_note="caseload mix, area of law, and appellate posture"),
            )
        )

    # --- Signal 2: government vs private prevailing rate ---
    # We approximate "the prevailing party's role" from the disposition + party roles.
    gov_wins = gov_total = priv_wins = priv_total = 0
    for r in rows:
        parties = (r.entities or {}).get("PARTY", [])
        if len(parties) < 2 or r.outcome not in ("plaintiff", "defendant"):
            continue
        roles = [classify_party_role(p) for p in parties[:2]]
        # Convention: first party ~ plaintiff/appellant, second ~ defendant/appellee.
        winner_idx = 0 if r.outcome == "plaintiff" else 1
        for idx, role in enumerate(roles):
            won = idx == winner_idx
            if role == "government":
                gov_total += 1
                gov_wins += int(won)
            else:
                priv_total += 1
                priv_wins += int(won)

    if gov_total and priv_total:
        test = two_proportion_ztest(gov_wins, gov_total, priv_wins, priv_total)
        signals.append(
            BiasSignal(
                metric="outcome.government_vs_private",
                description=(
                    f"Government parties prevailed in {test.rate_a:.0%} of applicable matters vs "
                    f"{test.rate_b:.0%} for private parties (difference {test.diff:+.0%})."
                ),
                effect_size=test.diff,
                p_value=test.p_value,
                detail={"gov_wins": gov_wins, "gov_total": gov_total,
                        "priv_wins": priv_wins, "priv_total": priv_total},
                caveats=build_caveats(
                    min(gov_total, priv_total),
                    base_confidence=0.5,
                    extra_limitations=(
                        "Party-role inference from captions is heuristic; the government is "
                        "structurally over-represented as a repeat litigant, which alone can drive "
                        "rate differences."
                    ),
                    confound_note="repeat-player effects, case selection, and area of law",
                ),
            )
        )

    return signals
