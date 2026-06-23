"""Pydantic request/response models. Every bias-bearing payload carries caveats."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Shared ethics envelope
# --------------------------------------------------------------------------- #
class Caveats(BaseModel):
    """Attached to every statistical signal Leviathan emits."""

    confidence: float = Field(..., description="0-1 heuristic confidence in this signal.")
    sample_size: int = Field(..., description="n the statistic was computed over.")
    sample_warning: str | None = Field(
        None, description="Set when n is below the configured minimum."
    )
    limitations: str = Field(..., description="Plain-language limits of this signal.")
    interpretation: str = Field(
        ..., description="Mandatory non-causal, no-intent interpretation note."
    )


class BiasSignal(BaseModel):
    metric: str
    description: str
    effect_size: float | None = None
    p_value: float | None = None
    p_value_adjusted: float | None = None
    detail: dict = Field(default_factory=dict)
    caveats: Caveats


# --------------------------------------------------------------------------- #
# Ingestion / case analysis
# --------------------------------------------------------------------------- #
class OpinionIn(BaseModel):
    case_name: str
    text: str
    judge_name: str | None = None
    court: str | None = None
    decided: date | None = None
    case_type: str | None = None
    citations: list[str] = Field(default_factory=list)
    source: str = "manual"
    external_id: str | None = None


class Entity(BaseModel):
    text: str
    label: str  # JUDGE, PARTY, STATUTE, ORG, ...


class AnalyzeResult(BaseModel):
    case_name: str
    outcome: str
    outcome_confidence: float
    tone_score: float
    party_tone: dict[str, float]
    entities: list[Entity]
    issues: list[str]
    citations: list[str]
    disclaimer: str


# --------------------------------------------------------------------------- #
# Judge profile & comparison
# --------------------------------------------------------------------------- #
class JudgeProfile(BaseModel):
    judge_id: int
    display_name: str
    n_opinions: int
    signals: list[BiasSignal]
    disclaimer: str


class CompareJudgesIn(BaseModel):
    judge_ids: list[int] = Field(..., min_length=2)
    case_type: str | None = None


class CompareJudgesResult(BaseModel):
    judges: list[JudgeProfile]
    cross_judge_signals: list[BiasSignal]
    disclaimer: str


# --------------------------------------------------------------------------- #
# Similar cases
# --------------------------------------------------------------------------- #
class SimilarCasesIn(BaseModel):
    text: str | None = None
    opinion_id: int | None = None
    top_k: int = 10
    case_type: str | None = None


class SimilarCase(BaseModel):
    opinion_id: int
    case_name: str
    judge: str | None
    court: str | None
    outcome: str | None
    similarity: float


class SimilarCasesResult(BaseModel):
    query_summary: str
    results: list[SimilarCase]
    outcome_comparison: BiasSignal | None
    disclaimer: str
