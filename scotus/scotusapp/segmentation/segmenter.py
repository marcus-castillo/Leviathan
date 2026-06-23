"""Segment a full SCOTUS opinion document into majority / concurrence / dissent / per-curiam parts.

SCOTUS opinions are concatenated in a consistent register: the Court's opinion first, then separate
writings introduced by headers like::

    JUSTICE KAGAN delivered the opinion of the Court.
    CHIEF JUSTICE ROBERTS, concurring.
    JUSTICE ALITO, with whom JUSTICE THOMAS joins, dissenting.
    PER CURIAM.

We split on those headers and classify each block by the role keyword, capturing the authoring
justice. This is a transparent heuristic (auditable), robust to the common phrasings; it is not a
learned parser. If no headers are found, the whole document is returned as a single majority segment.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Header forms. Captures: author (optional), role keyword.
# Examples matched:
#   "JUSTICE KAGAN delivered the opinion of the Court."
#   "Justice Sotomayor, concurring in part and dissenting in part."
#   "CHIEF JUSTICE ROBERTS, concurring in the judgment."
#   "PER CURIAM."
_HEADER_RE = re.compile(
    r"""(?P<full>
        (?:^|\n)\s*
        (?:
            (?P<percuriam>PER\s+CURIAM)\b
          |
            (?:(?:CHIEF\s+)?JUSTICE\s+(?P<author>[A-Z][A-Za-z'\-]+))
            (?P<rest>[^\n.]*?)
            \b(?P<role>delivered\s+the\s+opinion|concurring|dissenting|concur|dissent)\b
            [^.\n]*\.?          # rest of the header sentence only (NOT the opinion body)
        )
    )""",
    re.VERBOSE | re.IGNORECASE,
)


@dataclass
class Segment:
    kind: str          # majority | concurrence | dissent | per_curiam
    author: str | None
    text: str


def _classify(role: str, rest: str) -> str:
    blob = f"{rest} {role}".lower()
    # "concurring in part and dissenting in part" -> treat as dissent-bearing (mixed leans dissent
    # for divergence purposes) only if dissent present; otherwise concurrence.
    has_dissent = "dissent" in blob
    has_concur = "concur" in blob
    if "delivered the opinion" in blob:
        return "majority"
    if has_dissent and not has_concur:
        return "dissent"
    if has_dissent and has_concur:
        return "mixed"
    if has_concur:
        return "concurrence"
    return "concurrence"


def segment_opinion(text: str) -> list[Segment]:
    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        cleaned = text.strip()
        return [Segment(kind="majority", author=None, text=cleaned)] if cleaned else []

    segments: list[Segment] = []
    # Any preamble before the first header (syllabus/caption) is dropped from segment bodies.
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if m.group("percuriam"):
            kind, author = "per_curiam", None
        else:
            author = m.group("author")
            kind = _classify(m.group("role") or "", m.group("rest") or "")
        if body:
            segments.append(Segment(kind=kind, author=author, text=body))
    return segments
