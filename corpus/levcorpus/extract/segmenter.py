"""Lightweight opinion segmenter.

Federal opinions are loosely structured (caption → procedural posture → facts/background →
discussion → disposition). This splits text into sentences and into coarse sections using common
heading cues, so the structured extractor can pull facts / issue / ruling spans. Heuristic and
auditable — not a learned parser.
"""
from __future__ import annotations

import re

_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

_SECTION_CUES = {
    "background": re.compile(r"\b(background|factual background|facts|statement of facts)\b", re.I),
    "issue": re.compile(r"\b(question presented|issue|we must decide|the issue is|whether)\b", re.I),
    "discussion": re.compile(r"\b(discussion|analysis|we turn to|standard of review)\b", re.I),
    "disposition": re.compile(
        r"\b(conclusion|for the foregoing reasons|accordingly|we (affirm|reverse|vacate|remand)|"
        r"it is (so )?ordered|the (motion|petition|judgment) is)\b",
        re.I,
    ),
}


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_RE.split(text) if s.strip()]


def sections(text: str) -> dict[str, str]:
    """Bucket sentences into coarse sections by the first matching cue seen.

    A sentence stays in the most recently opened section; the leading sentences before any cue go to
    'caption'. This is a best-effort grouping, not a strict parse.
    """
    out: dict[str, list[str]] = {k: [] for k in ("caption", *_SECTION_CUES)}
    current = "caption"
    for sent in sentences(text):
        for name, rx in _SECTION_CUES.items():
            if rx.search(sent):
                current = name
                break
        out[current].append(sent)
    return {k: " ".join(v).strip() for k, v in out.items()}
