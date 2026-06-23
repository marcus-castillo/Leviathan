"""SQLAlchemy ORM models for opinions, judges, courts, and derived NLP artifacts."""
from __future__ import annotations

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

# all-MiniLM-L6-v2 produces 384-dim embeddings.
EMBEDDING_DIM = 384


class Court(Base):
    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    jurisdiction: Mapped[str | None] = mapped_column(String(64))  # e.g. "federal", "9th-cir"

    opinions: Mapped[list["Opinion"]] = relationship(back_populates="court")


class Judge(Base):
    __tablename__ = "judges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    normalized_name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(256))

    opinions: Mapped[list["Opinion"]] = relationship(back_populates="judge")


class Opinion(Base):
    __tablename__ = "opinions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Stable external id (e.g. CourtListener cluster id) for idempotent ingestion.
    source: Mapped[str] = mapped_column(String(32), default="manual")
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)

    case_name: Mapped[str] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(Text)
    decided: Mapped[date | None] = mapped_column(Date, index=True)
    case_type: Mapped[str | None] = mapped_column(String(64), index=True)  # civil-rights, immigration...

    court_id: Mapped[int | None] = mapped_column(ForeignKey("courts.id"), index=True)
    judge_id: Mapped[int | None] = mapped_column(ForeignKey("judges.id"), index=True)

    # Raw metadata bag (citations list, party descriptors, etc.)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    court: Mapped[Court | None] = relationship(back_populates="opinions")
    judge: Mapped[Judge | None] = relationship(back_populates="opinions")
    analysis: Mapped["Analysis | None"] = relationship(
        back_populates="opinion", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_opinion_source_extid"),)


class Analysis(Base):
    """Cached output of the NLP pipeline for one opinion."""

    __tablename__ = "analyses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    opinion_id: Mapped[int] = mapped_column(ForeignKey("opinions.id"), unique=True, index=True)

    # Outcome classification.
    outcome: Mapped[str | None] = mapped_column(String(32))  # plaintiff / defendant / mixed / unknown
    outcome_confidence: Mapped[float | None] = mapped_column(Float)

    # Tone of ruling language (NOT sentiment toward a person). Range roughly [-1, 1].
    tone_score: Mapped[float | None] = mapped_column(Float)

    # Structured extractions: entities, issues, citations, party-tagged tone spans.
    entities: Mapped[dict] = mapped_column(JSONB, default=dict)
    issues: Mapped[list] = mapped_column(JSONB, default=list)
    citations: Mapped[list] = mapped_column(JSONB, default=list)
    party_tone: Mapped[dict] = mapped_column(JSONB, default=dict)  # {"government": x, "private": y}

    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    opinion: Mapped[Opinion] = relationship(back_populates="analysis")
