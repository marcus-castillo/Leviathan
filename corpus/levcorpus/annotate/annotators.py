"""Automatic annotation layer.

Reuses the backend NLP pipeline (outcome classifier, issue/topic lexicon, tone scorer) and maps its
output into the standardized annotation schema. ``decision_direction`` is derived structurally from
the outcome — it is NOT an ideological coding.

Every label here is a weak, automatically generated proxy. Treat accordingly.
"""
from __future__ import annotations

from levcorpus.schema import Annotations, DecisionDirection, Outcome

# Map pipeline outcome -> structural decision direction.
_DIRECTION = {
    "plaintiff": DecisionDirection.plaintiff_appellant,
    "defendant": DecisionDirection.defendant_appellee,
    "mixed": DecisionDirection.mixed,
    "unknown": DecisionDirection.unknown,
}


def annotate(text: str, case_name: str | None = None, citations: list[str] | None = None,
             case_type_hint: str | None = None) -> tuple[Annotations, dict]:
    """Return (Annotations, raw_pipeline_dict). The raw dict carries entities/party_tone for reuse."""
    from app.nlp.pipeline import get_pipeline  # backend reuse

    out = get_pipeline().run(text, case_name=case_name, citations=citations or [])

    case_type = case_type_hint or (out.issues[0] if out.issues else "unknown")
    ann = Annotations(
        outcome=Outcome(out.outcome),
        outcome_confidence=out.outcome_confidence,
        case_type=case_type,
        topic=out.issues,
        sentiment_proxy=out.tone_score,
        decision_direction=_DIRECTION.get(out.outcome, DecisionDirection.unknown),
    )
    raw = {
        "entities": out.entities,
        "party_tone": out.party_tone,
        "citations": out.citations,
        "issues": out.issues,
    }
    return ann, raw
