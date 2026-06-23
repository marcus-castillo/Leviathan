"""End-to-end orchestration: collect -> preprocess -> embed -> export."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from levcorpus.annotate import annotate
from levcorpus.db import CorpusRecordRow, RawDocument
from levcorpus.embed import embed_text, embedding_model_name
from levcorpus.extract import extract_structured
from levcorpus.schema import (
    CaseRecord,
    Parties,
    make_judge_id,
    make_record_id,
    text_hash,
)
from levcorpus.versioning import VersionRegistry


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _party_roles(parties: list[str]) -> dict[str, str]:
    from app.nlp.pipeline import classify_party_role  # backend reuse

    return {p: classify_party_role(p) for p in parties}


def build_record(raw: RawDocument) -> CaseRecord:
    """Run extraction + annotation for one raw document and assemble a standardized record."""
    from app.ingestion.base import normalize_judge_name  # backend reuse

    citations = (raw.meta or {}).get("citations", [])
    structured = extract_structured(raw.text, case_name=raw.case_name)
    ann, raw_nlp = annotate(raw.text, case_name=raw.case_name, citations=citations,
                            case_type_hint=(raw.meta or {}).get("case_type"))

    norm = normalize_judge_name(raw.judge_name) if raw.judge_name else None
    parties = structured.all_parties or (raw.meta or {}).get("parties", [])

    return CaseRecord(
        record_id=make_record_id(raw.source, raw.external_id, raw.text),
        source=raw.source,
        source_url=raw.source_url,
        external_id=raw.external_id,
        license=(raw.meta or {}).get("license", "Public domain / CourtListener terms"),
        case_name=raw.case_name,
        court=raw.court,
        jurisdiction=raw.jurisdiction,
        judge=raw.judge_name,
        judge_id=make_judge_id(norm),
        decided=_parse_date(raw.decided),
        parties=Parties(
            plaintiff_or_appellant=structured.parties_plaintiff,
            defendant_or_appellee=structured.parties_defendant,
            all_parties=parties,
            party_roles=_party_roles(parties),
        ),
        citations=raw_nlp.get("citations", citations),
        facts_summary=structured.facts_summary,
        legal_issue=structured.legal_issue,
        ruling=structured.ruling,
        text_sha256=text_hash(raw.text),
        annotations=ann,
        embedding=None,
        embedding_model=None,
    )


def preprocess_pending(db: Session, *, reprocess: bool = False, limit: int | None = None) -> int:
    """Build standardized records for raw docs that don't have one yet (or all, if reprocess)."""
    stmt = select(RawDocument)
    if not reprocess:
        stmt = stmt.outerjoin(CorpusRecordRow, CorpusRecordRow.raw_id == RawDocument.id).where(
            CorpusRecordRow.id.is_(None)
        )
    if limit:
        stmt = stmt.limit(limit)

    raws = db.execute(stmt).scalars().all()
    count = 0
    for raw in raws:
        record = build_record(raw)
        payload = record.model_dump(mode="json", exclude={"embedding"})

        row = db.execute(
            select(CorpusRecordRow).where(CorpusRecordRow.raw_id == raw.id)
        ).scalar_one_or_none()
        if row is None:
            row = CorpusRecordRow(raw_id=raw.id, record_id=record.record_id)
            db.add(row)
        row.record_id = record.record_id
        row.payload = payload
        row.schema_version = record.schema_version
        count += 1
        if count % 20 == 0:
            db.commit()
    db.commit()
    return count


def embed_pending(db: Session, *, reembed: bool = False, limit: int | None = None) -> int:
    """Compute and store case-similarity embeddings for records missing them."""
    stmt = select(CorpusRecordRow)
    if not reembed:
        stmt = stmt.where(CorpusRecordRow.has_embedding.is_(False))
    if limit:
        stmt = stmt.limit(limit)

    rows = db.execute(stmt).scalars().all()
    model = embedding_model_name()
    count = 0
    for row in rows:
        raw = db.get(RawDocument, row.raw_id)
        if raw is None:
            continue
        row.embedding = embed_text(raw.text)
        row.has_embedding = True
        payload = dict(row.payload)
        payload["embedding_model"] = model
        row.payload = payload
        count += 1
        if count % 20 == 0:
            db.commit()
    db.commit()
    return count


def export_dataset(
    db: Session,
    *,
    formats: list[str],
    bump: str = "minor",
    version: str | None = None,
    note: str = "",
    include_embeddings: bool = True,
) -> dict:
    """Materialize all standardized records (with embeddings) and release a new dataset version."""
    rows = db.execute(select(CorpusRecordRow)).scalars().all()
    records: list[dict] = []
    for row in rows:
        rec = dict(row.payload)
        if include_embeddings and row.embedding is not None:
            rec["embedding"] = list(row.embedding)
        else:
            rec["embedding"] = None
        records.append(rec)

    registry = VersionRegistry()
    return registry.release(records, formats=formats, bump=bump,
                            explicit_version=version, note=note)
