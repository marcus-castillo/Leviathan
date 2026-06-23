"""levcorpus persistence: a raw-document staging table and a standardized-record table.

Shares the same Postgres instance as the backend (same ``DATABASE_URL``) but owns its own tables, so
the two systems don't fight over schema. Embeddings reuse the backend's 384-dim MiniLM space.
"""
from __future__ import annotations

from collections.abc import Generator
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from levcorpus.config import DATABASE_URL

# Reuse the backend's embedding dimensionality so vectors are interoperable.
try:
    from app.models import EMBEDDING_DIM
except Exception:  # pragma: no cover - backend not importable in some envs
    EMBEDDING_DIM = 384

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class RawDocument(Base):
    """As-collected opinion text + raw metadata, before standardization."""

    __tablename__ = "corpus_raw"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(32), index=True)
    external_id: Mapped[str | None] = mapped_column(String(128), index=True)
    source_url: Mapped[str | None] = mapped_column(String(512))

    case_name: Mapped[str] = mapped_column(String(512))
    text: Mapped[str] = mapped_column(Text)
    court: Mapped[str | None] = mapped_column(String(64))
    jurisdiction: Mapped[str | None] = mapped_column(String(64))
    judge_name: Mapped[str | None] = mapped_column(String(256))
    decided: Mapped[str | None] = mapped_column(String(32))  # ISO string; parsed downstream
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)  # citations, parties, license, ...

    collected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    record: Mapped["CorpusRecordRow | None"] = relationship(
        back_populates="raw", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_corpus_raw_src_extid"),)


class CorpusRecordRow(Base):
    """Standardized record: the full ``CaseRecord`` payload as JSONB + a queryable embedding."""

    __tablename__ = "corpus_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    raw_id: Mapped[int] = mapped_column(ForeignKey("corpus_raw.id"), index=True)

    payload: Mapped[dict] = mapped_column(JSONB)  # serialized CaseRecord (minus embedding)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))

    schema_version: Mapped[str] = mapped_column(String(16))
    has_embedding: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    raw: Mapped[RawDocument] = relationship(back_populates="record")


def get_session() -> Generator[Session, None, None]:
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
