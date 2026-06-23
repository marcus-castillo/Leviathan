"""Ethics guardrails enforced on every bias-bearing output.

The design intent: make it *structurally hard* for Leviathan to overclaim. Confidence scores,
sample-size warnings, and limitations strings are not optional decorations — they are constructed
here and required by the schema (`Caveats`). Narrative text is scrubbed of intent vocabulary.
"""
from __future__ import annotations

import re

from app.config import settings
from app.schemas import Caveats

GLOBAL_DISCLAIMER = (
    "Leviathan reports statistical disparities in text and outcomes only. It does NOT measure "
    "judicial intent, bias, or prejudice, and cannot establish causation. Disparities may stem "
    "from caseload composition, the governing law, selection effects, or sampling noise. Treat all "
    "results as hypotheses requiring qualified human review of the underlying opinions."
)

# Vocabulary that asserts mental state / wrongdoing. Blocked from generated narratives.
_INTENT_PATTERNS = [
    r"\b(biased|prejudic\w+|bigot\w*|racist|sexist|corrupt\w*)\b",
    r"\b(intend\w*|intent\w*|deliberat\w*|willful\w*|malicious\w*|malice)\b",
    r"\b(discriminat\w+ against|unfair\w*|injustice)\b",
    r"\b(proves?|demonstrat\w+ that .* is)\b",
]
_INTENT_RE = re.compile("|".join(_INTENT_PATTERNS), flags=re.IGNORECASE)

# Neutral replacement phrasing for any flagged term.
_NEUTRAL = "a statistical disparity"


def enforce_no_intent_language(text: str) -> str:
    """Replace intent/causal vocabulary with neutral statistical phrasing.

    This is a safety net for any human-written or template narrative that slips through. Generated
    explanations are built from neutral templates in the first place; this guarantees the invariant.
    """
    return _INTENT_RE.sub(_NEUTRAL, text)


def build_caveats(
    sample_size: int,
    *,
    base_confidence: float = 0.6,
    extra_limitations: str = "",
    confound_note: str = "caseload composition, area of law, and appellate posture",
) -> Caveats:
    """Construct the mandatory ethics envelope for a signal.

    Confidence is penalized for small samples; below ``MIN_SAMPLE_SIZE`` a warning is attached and
    confidence is floored so the UI surfaces the unreliability prominently.
    """
    min_n = settings.min_sample_size

    if sample_size <= 0:
        confidence = 0.0
    elif sample_size < min_n:
        # Linear penalty toward the minimum; never report high confidence on thin data.
        confidence = round(min(base_confidence, 0.4) * (sample_size / min_n), 3)
    else:
        # Mild logarithmic-ish boost, capped.
        confidence = round(min(0.95, base_confidence + 0.1 * (sample_size >= 4 * min_n)), 3)

    warning = None
    if sample_size < min_n:
        warning = (
            f"Sample size n={sample_size} is below the minimum reliable threshold "
            f"(n={min_n}). This figure is shown for transparency but should not be relied upon."
        )

    limitations = (
        f"Computed over n={sample_size} opinions from a non-random sample. "
        f"Likely confounds not controlled for: {confound_note}. "
        "Outcome and tone labels are model-generated and noisy."
    )
    if extra_limitations:
        limitations = f"{limitations} {extra_limitations}"

    interpretation = (
        "This is a descriptive association, not evidence of intent or wrongdoing, and does not "
        "establish a causal effect of the judge."
    )

    return Caveats(
        confidence=confidence,
        sample_size=sample_size,
        sample_warning=warning,
        limitations=enforce_no_intent_language(limitations),
        interpretation=interpretation,
    )
