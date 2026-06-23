"""Tone analysis of ruling language.

IMPORTANT FRAMING: this measures the *tone of the text* (formal/neutral vs. critical/approving
phrasing), a property of the writing — NOT a litigant's feelings and NOT the judge's attitude toward a
party. We deliberately call it "tone", expose it as a continuous score in roughly [-1, 1], and tag
tone in sentences that mention each party so downstream bias metrics can compare *language*, never
infer motive.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Small, auditable tone lexicon over judicial-register language. Transparent by design.
_NEGATIVE = {
    "meritless", "frivolous", "unpersuasive", "implausible", "baseless", "fails", "failed",
    "unavailing", "rejected", "without merit", "conclusory", "insufficient", "waived",
    "disingenuous", "cursory", "unsupported",
}
_POSITIVE = {
    "persuasive", "compelling", "meritorious", "well-pleaded", "plausible", "supported",
    "credible", "convincing", "reasonable", "sufficient", "established",
}

_WORD_RE = re.compile(r"[A-Za-z][A-Za-z\-]+")
_SENT_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class ToneResult:
    overall: float
    by_party: dict[str, float] = field(default_factory=dict)


def _score_tokens(tokens: list[str]) -> float:
    pos = sum(t in _POSITIVE for t in tokens)
    neg = sum(t in _NEGATIVE for t in tokens)
    if pos + neg == 0:
        return 0.0
    return (pos - neg) / (pos + neg)


def analyze_tone(text: str, parties: list[str] | None = None) -> ToneResult:
    """Compute overall tone and, where party names are given, tone of sentences mentioning each.

    ``parties`` may include role hints like "government" / "private"; we also bucket by these roles
    when a party name resolves to one (see ``bias.sentiment_bias`` for role mapping).
    """
    tokens = [w.lower() for w in _WORD_RE.findall(text)]
    overall = _score_tokens(tokens)

    by_party: dict[str, float] = {}
    if parties:
        sentences = _SENT_RE.split(text)
        for party in parties:
            key = party.lower()
            relevant = [s for s in sentences if key in s.lower()]
            if relevant:
                toks = [w.lower() for s in relevant for w in _WORD_RE.findall(s)]
                by_party[party] = round(_score_tokens(toks), 4)

    return ToneResult(overall=round(overall, 4), by_party=by_party)
