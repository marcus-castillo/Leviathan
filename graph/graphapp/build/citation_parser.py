"""Detect citations in opinion text and classify their *treatment* (edge type).

Treatment is inferred from signal language in the sentence(s) around a citation. This is a
transparent, auditable heuristic — not a learned model — so every edge type traces to matched cues.
Order matters: a stronger negative/positive signal wins over a generic cite.
"""
from __future__ import annotations

import re

# Map treatment -> regex of signal phrases (checked against the local context window).
_TREATMENT_CUES: list[tuple[str, re.Pattern]] = [
    ("OVERRULES", re.compile(r"\b(overrul\w+|abrogat\w+|is no longer good law|we reject .* holding)\b", re.I)),
    ("DISTINGUISHES", re.compile(r"\b(distinguish\w+|is distinguishable|are distinguishable|unlike)\b", re.I)),
    ("FOLLOWS", re.compile(r"\b(we follow|following|adher\w+ to|consistent with|in accord with|reaffirm\w*)\b", re.I)),
]

# A loose reporter/citation pattern, e.g. "Chevron U.S.A. Inc. v. NRDC", "Terry v. Ohio",
# "347 U.S. 483". Used only to locate citation contexts when explicit edges aren't provided.
_CASE_CITE_RE = re.compile(
    r"([A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,4}\s+v\.?\s+[A-Z][A-Za-z.'\-]+(?:\s+[A-Z][A-Za-z.'\-]+){0,4})"
    r"|(\b\d{1,3}\s+U\.?\s?S\.?\s+\d{1,4}\b)"
)

def classify_treatment(context: str) -> str:
    """Return the citation edge type implied by ``context`` (default 'CITES')."""
    for treatment, rx in _TREATMENT_CUES:
        if rx.search(context):
            return treatment
    return "CITES"


def extract_citation_contexts(text: str, window: int = 200) -> list[dict]:
    """Find candidate case citations and the treatment implied by surrounding text.

    Returns ``[{"citation": str, "treatment": str, "context": str}, ...]``, de-duplicated by citation.

    We match over the *full text* (not sentence-split) and take a +/- ``window``-character context
    around each hit. Sentence splitting is unreliable here because legal citations are full of periods
    (``U.S.A.``, ``Inc.``, ``v.``) that naive splitters mistake for sentence boundaries.
    """
    matches = list(_CASE_CITE_RE.finditer(text))
    out: dict[str, dict] = {}
    for i, m in enumerate(matches):
        cite = re.sub(r"\s+", " ", (m.group(0) or "").strip())
        if not cite:
            continue
        # Clamp the context so a cue near one citation isn't attributed to an adjacent one.
        prev_end = matches[i - 1].end() if i > 0 else 0
        next_start = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        lo = max(prev_end, m.start() - window)
        hi = min(next_start, m.end() + window)
        context = text[lo:hi]
        treatment = classify_treatment(context)
        if cite not in out or (out[cite]["treatment"] == "CITES" and treatment != "CITES"):
            out[cite] = {"citation": cite, "treatment": treatment, "context": context}
    return list(out.values())
