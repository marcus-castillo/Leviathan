"""SQLAlchemy models for SCOTUS cases, opinion segments, and justices.

Shares the Postgres instance with the rest of Leviathan but owns its own ``scotus_*`` tables.
Embeddings reuse the backend's 384-dim MiniLM space.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from scotusapp.config import settings

EMBEDDING_DIM = 384

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class Justice(Base):
    __tablename__ = "scotus_justice"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    # Style fingerprint = mean of authored-segment embeddings.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    n_segments: Mapped[int] = mapped_column(Integer, default=0)

    segments: Mapped[list["OpinionSegment"]] = relationship(back_populates="justice")


class Case(Base):
    __tablename__ = "scotus_case"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str | None] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(512))
    term: Mapped[int | None] = mapped_column(Integer, index=True)  # SCOTUS term year
    citation: Mapped[str | None] = mapped_column(String(128))
    decided: Mapped[str | None] = mapped_column(String(32))
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)

    segments: Mapped[list["OpinionSegment"]] = relationship(
        back_populates="case", cascade="all, delete-orphan"
    )


class OpinionSegment(Base):
    """One segment of a case's opinion: majority / concurrence / dissent / per-curiam."""

    __tablename__ = "scotus_segment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("scotus_case.id"), index=True)
    justice_id: Mapped[int | None] = mapped_column(ForeignKey("scotus_justice.id"), index=True)

    kind: Mapped[str] = mapped_column(String(24), index=True)  # majority|concurrence|dissent|per_curiam
    author_name: Mapped[str | None] = mapped_column(String(128))
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    case: Mapped[Case] = relationship(back_populates="segments")
    justice: Mapped[Justice | None] = relationship(back_populates="segments")

    __table_args__ = (UniqueConstraint("case_id", "kind", "author_name", name="uq_segment"),)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
