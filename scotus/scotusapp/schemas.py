"""Pydantic response models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class IngestResult(BaseModel):
    cases: int
    segments: int
    justices: int
    disclaimer: str


class DivergenceResult(BaseModel):
    case_id: int
    case_name: str
    majority_terms: list[tuple[str, float]]
    dissent_terms: list[tuple[str, float]]
    note: str | None = None
    disclaimer: str


class TopicsResult(BaseModel):
    topics: list[dict]
    theme_distribution: dict[str, int]
    disclaimer: str


class JusticeProfile(BaseModel):
    slug: str
    name: str
    n_segments: int
    distinctive_terms: list[tuple[str, float]]
    nearest: list[dict]
    disclaimer: str


class SimilarityMap(BaseModel):
    justices: list[str]
    matrix: list[list[float]]
    clusters: list[dict]
    disclaimer: str


class SimilarCasesResult(BaseModel):
    query_case: str | None
    results: list[dict]
    disclaimer: str


class EvolutionResult(BaseModel):
    by_term: list[dict] = Field(default_factory=list)
    disclaimer: str
