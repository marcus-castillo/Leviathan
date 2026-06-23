"""Orchestrates the full NLP pipeline for one opinion.

Heavy resources (spaCy model, transformer classifier, embedding encoder) are loaded once and cached
on a process-global singleton via ``get_pipeline()``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache

from app.config import settings
from app.nlp import entities as ent
from app.nlp.issues import tag_issues
from app.nlp.outcome import OutcomeClassifier
from app.nlp.tone import analyze_tone


@dataclass
class PipelineOutput:
    outcome: str
    outcome_confidence: float
    tone_score: float
    party_tone: dict[str, float]
    entities: dict[str, list[str]]
    issues: list[str]
    citations: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


# Map raw party strings to coarse roles used by the bias engine.
_GOV_MARKERS = (
    "united states", "u.s.", "people", "state of", "commissioner", "secretary",
    "department", "irs", "sec", "epa", "ins", "dhs", "warden", "director",
)


def classify_party_role(party: str) -> str:
    low = party.lower()
    return "government" if any(m in low for m in _GOV_MARKERS) else "private"


class NLPPipeline:
    def __init__(self) -> None:
        self._nlp = self._load_spacy()
        self._outcome = OutcomeClassifier()

    @staticmethod
    def _load_spacy():
        try:
            import spacy

            return spacy.load(settings.spacy_model)
        except Exception:  # pragma: no cover - model may be absent in minimal envs
            return None

    def run(self, text: str, case_name: str | None = None,
            citations: list[str] | None = None) -> PipelineOutput:
        doc = self._nlp(text[:100_000]) if self._nlp is not None else None

        ents = ent.extract_entities(doc, case_name, text)
        issues = tag_issues(text)
        outcome = self._outcome.predict(text)

        parties = ents.get("PARTY", [])
        tone = analyze_tone(text, parties=parties)

        # Re-bucket party tone by coarse role (government vs private) for bias metrics.
        party_tone: dict[str, float] = dict(tone.by_party)
        role_scores: dict[str, list[float]] = {}
        for party, score in tone.by_party.items():
            role_scores.setdefault(classify_party_role(party), []).append(score)
        for role, scores in role_scores.items():
            party_tone[role] = round(sum(scores) / len(scores), 4)

        cites = list(citations or [])
        for s in ents.get("STATUTE", []):
            if s not in cites:
                cites.append(s)

        return PipelineOutput(
            outcome=outcome.label,
            outcome_confidence=outcome.confidence,
            tone_score=tone.overall,
            party_tone=party_tone,
            entities=ents,
            issues=issues,
            citations=cites,
        )


@lru_cache
def get_pipeline() -> NLPPipeline:
    return NLPPipeline()
