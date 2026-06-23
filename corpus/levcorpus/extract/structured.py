"""Extract structured fields (facts / issue / ruling / parties) from an opinion.

Reuses the backend's entity rules for parties/statutes; adds extractive heuristics for the
narrative fields. All outputs are extractive (spans copied from the text), never abstractive.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from levcorpus.extract import segmenter


@dataclass
class StructuredFields:
    facts_summary: str | None = None
    legal_issue: str | None = None
    ruling: str | None = None
    parties_plaintiff: str | None = None
    parties_defendant: str | None = None
    all_parties: list[str] = field(default_factory=list)


def _first_n_sentences(blob: str, n: int) -> str | None:
    sents = segmenter.sentences(blob)
    return " ".join(sents[:n]) if sents else None


def _find_issue(text: str, sec: dict[str, str]) -> str | None:
    # Prefer an explicit "whether ..." sentence; else the opening of the issue section.
    for sent in segmenter.sentences(sec.get("issue", "") or text):
        low = sent.lower()
        if low.startswith("whether") or "question presented" in low or "we must decide" in low:
            return sent
    return _first_n_sentences(sec.get("issue", ""), 1)


def extract_structured(text: str, case_name: str | None = None) -> StructuredFields:
    from app.nlp.entities import extract_parties  # backend reuse

    sec = segmenter.sections(text)

    facts = _first_n_sentences(sec.get("background", ""), 4) or _first_n_sentences(
        sec.get("caption", ""), 3
    )
    issue = _find_issue(text, sec)
    ruling = sec.get("disposition") or _last_n_sentences(text, 2)

    parties = extract_parties(case_name, text)
    return StructuredFields(
        facts_summary=facts,
        legal_issue=issue,
        ruling=ruling or None,
        parties_plaintiff=parties[0] if parties else None,
        parties_defendant=parties[1] if len(parties) > 1 else None,
        all_parties=parties,
    )


def _last_n_sentences(text: str, n: int) -> str | None:
    sents = segmenter.sentences(text)
    return " ".join(sents[-n:]) if sents else None
