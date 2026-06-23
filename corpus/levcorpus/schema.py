"""Canonical, versioned dataset record schema.

The contract for the exported dataset. Bump ``SCHEMA_VERSION`` (semver) on any field change; the
versioning system records a field-level diff between dataset releases.
"""
from __future__ import annotations

import hashlib
from datetime import date, datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

SCHEMA_VERSION = "1.0.0"

SENTIMENT_PROXY_NOTE = (
    "WEAK PROXY. Lexical tone of the ruling language only; not a measure of sentiment toward any "
    "party and not validated against human judgment. Do not use as ground truth."
)


class Outcome(str, Enum):
    plaintiff = "plaintiff"
    defendant = "defendant"
    mixed = "mixed"
    unknown = "unknown"


class DecisionDirection(str, Enum):
    """STRUCTURAL prevailing-party label — NOT an ideological/political coding."""

    plaintiff_appellant = "plaintiff_appellant_favored"
    defendant_appellee = "defendant_appellee_favored"
    mixed = "mixed"
    unknown = "unknown"


class Parties(BaseModel):
    plaintiff_or_appellant: str | None = None
    defendant_or_appellee: str | None = None
    all_parties: list[str] = Field(default_factory=list)
    party_roles: dict[str, str] = Field(default_factory=dict)  # name -> government|private


class Annotations(BaseModel):
    outcome: Outcome = Outcome.unknown
    outcome_confidence: float = 0.0
    case_type: str = "unknown"
    topic: list[str] = Field(default_factory=list)
    sentiment_proxy: float = 0.0
    sentiment_proxy_note: str = SENTIMENT_PROXY_NOTE
    decision_direction: DecisionDirection = DecisionDirection.unknown


class CaseRecord(BaseModel):
    # identity / provenance
    record_id: str
    source: str
    source_url: str | None = None
    external_id: str | None = None
    license: str = "Public domain (U.S. govt work) / subject to CourtListener terms"

    # metadata
    case_name: str
    court: str | None = None
    jurisdiction: str | None = None
    judge: str | None = None
    judge_id: str | None = None
    decided: date | None = None
    parties: Parties = Field(default_factory=Parties)
    citations: list[str] = Field(default_factory=list)

    # extracted structure
    facts_summary: str | None = None
    legal_issue: str | None = None
    ruling: str | None = None
    text_sha256: str

    # annotation layer
    annotations: Annotations = Field(default_factory=Annotations)

    # bias-research / similarity
    embedding: list[float] | None = None
    embedding_model: str | None = None

    # versioning
    schema_version: str = SCHEMA_VERSION
    dataset_version: str | None = None
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_record_id(source: str, external_id: str | None, text: str) -> str:
    basis = f"{source}|{external_id or ''}|{text_hash(text)}"
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def make_judge_id(normalized_name: str | None) -> str | None:
    if not normalized_name:
        return None
    return "j_" + hashlib.sha1(normalized_name.encode("utf-8")).hexdigest()[:12]


def schema_field_names() -> set[str]:
    """Flat dotted field set used for schema diffing across versions."""
    names: set[str] = set()

    def walk(model: type[BaseModel], prefix: str = "") -> None:
        for fname, field in model.model_fields.items():
            dotted = f"{prefix}{fname}"
            ann = field.annotation
            if isinstance(ann, type) and issubclass(ann, BaseModel):
                walk(ann, dotted + ".")
            else:
                names.add(dotted)

    walk(CaseRecord)
    return names
