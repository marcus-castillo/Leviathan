"""Entity extraction: judges, parties, statutes, orgs.

Uses spaCy NER as a base and augments with legal-domain rules (statute citations, "v." party
splitting, signal phrases for the authoring judge).
"""
from __future__ import annotations

import re

# e.g. "42 U.S.C. § 1983", "Fed. R. Civ. P. 12(b)(6)", "18 U.S.C. 924(c)"
STATUTE_RE = re.compile(
    r"\b\d+\s+U\.?S\.?C\.?\s*§*\s*\d+[A-Za-z0-9()]*"
    r"|Fed\.?\s*R\.?\s*(?:Civ|Crim|App|Evid)\.?\s*P\.?\s*\d+[A-Za-z0-9()]*",
    flags=re.IGNORECASE,
)

# Authoring-judge signal phrases common in federal opinions.
JUDGE_SIGNAL_RE = re.compile(
    r"(?:^|\n)\s*([A-Z][A-Za-z.\-]+(?:\s+[A-Z][A-Za-z.\-]+){0,3}),?\s+"
    r"(?:Circuit |District |Chief )?Judge[.,:]",
)

# "Smith v. Jones" style captions.
CAPTION_RE = re.compile(r"([A-Z][\w.,'\-& ]+?)\s+v\.?\s+([A-Z][\w.,'\-& ]+)")


def extract_statutes(text: str) -> list[str]:
    seen: dict[str, None] = {}
    for m in STATUTE_RE.finditer(text):
        seen.setdefault(re.sub(r"\s+", " ", m.group(0).strip()), None)
    return list(seen)


def extract_parties(case_name: str | None, text: str) -> list[str]:
    parties: list[str] = []
    source = case_name or text[:400]
    m = CAPTION_RE.search(source)
    if m:
        parties = [m.group(1).strip(" ,"), m.group(2).strip(" ,")]
    return parties


def guess_authoring_judge(text: str) -> str | None:
    m = JUDGE_SIGNAL_RE.search(text)
    return m.group(1).strip() if m else None


def extract_entities(doc, case_name: str | None, text: str) -> dict[str, list[str]]:
    """Combine spaCy NER with legal rules. ``doc`` is a spaCy Doc (or None)."""
    out: dict[str, list[str]] = {"PERSON": [], "ORG": [], "STATUTE": [], "PARTY": [], "JUDGE": []}

    if doc is not None:
        for ent in doc.ents:
            if ent.label_ in ("PERSON", "ORG", "GPE", "LAW"):
                bucket = "ORG" if ent.label_ in ("ORG", "GPE") else "PERSON"
                if ent.label_ == "LAW":
                    bucket = "STATUTE"
                if ent.text not in out[bucket]:
                    out[bucket].append(ent.text)

    for s in extract_statutes(text):
        if s not in out["STATUTE"]:
            out["STATUTE"].append(s)

    out["PARTY"] = extract_parties(case_name, text)

    judge = guess_authoring_judge(text)
    if judge:
        out["JUDGE"] = [judge]

    return out
