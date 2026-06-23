"""Explainability layer.

Turns a raw ``BiasSignal`` into a human-readable, intent-free narrative: a statistical explanation,
a confidence statement, a dataset-size warning, and a limitations disclaimer. All text passes through
the no-intent guardrail before being returned.
"""
from __future__ import annotations

from app.ethics.guardrails import enforce_no_intent_language
from app.schemas import BiasSignal


def _significance_phrase(signal: BiasSignal) -> str:
    p = signal.p_value_adjusted if signal.p_value_adjusted is not None else signal.p_value
    if p is None:
        return "No hypothesis test applies to this descriptive profile."
    label = "FDR-adjusted " if signal.p_value_adjusted is not None else ""
    if p < 0.01:
        strength = "unlikely to be due to chance alone under the test's assumptions"
    elif p < 0.05:
        strength = "marginally distinguishable from chance under the test's assumptions"
    else:
        strength = "NOT statistically distinguishable from chance"
    return f"The {label}p-value is {p:.4f}; the difference is {strength}."


def explain(signal: BiasSignal) -> dict:
    """Return a structured, plain-language explanation for one signal."""
    c = signal.caveats
    statistical = (
        f"{signal.description} "
        f"{_significance_phrase(signal)} "
        f"Effect size: {signal.effect_size if signal.effect_size is not None else 'n/a'}."
    )

    confidence_stmt = (
        f"Heuristic confidence in this signal: {c.confidence:.0%}. "
        + ("Confidence is reduced because of the small sample. " if c.sample_warning else "")
    )

    return {
        "metric": signal.metric,
        "statistical_explanation": enforce_no_intent_language(statistical),
        "confidence_score": c.confidence,
        "confidence_statement": confidence_stmt,
        "dataset_size_warning": c.sample_warning
        or f"Sample size n={c.sample_size} meets the minimum threshold, but remains a non-random sample.",
        "limitations": c.limitations,
        "interpretation": c.interpretation,
    }


def explain_all(signals: list[BiasSignal]) -> list[dict]:
    return [explain(s) for s in signals]
