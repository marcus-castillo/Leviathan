"""Collect opinions from the CourtListener API into the raw staging table.

Reuses the backend's ``CourtListenerClient`` (HTTP + auth + text extraction); persistence is local to
the corpus so we keep the raw provenance separate from the live API's tables.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from levcorpus.db import RawDocument


def _upsert_raw(db: Session, **kw) -> bool:
    """Insert or update a raw doc keyed on (source, external_id). Returns True if newly inserted."""
    existing = db.execute(
        select(RawDocument).where(
            RawDocument.source == kw["source"], RawDocument.external_id == kw["external_id"]
        )
    ).scalar_one_or_none()
    if existing:
        for k, v in kw.items():
            setattr(existing, k, v)
        return False
    db.add(RawDocument(**kw))
    return True


def collect_courtlistener(
    db: Session,
    *,
    court: str | None = None,
    query: str | None = None,
    limit: int = 25,
) -> int:
    """Collect up to ``limit`` opinions; returns the number of new raw documents inserted."""
    from app.ingestion.courtlistener import CourtListenerClient  # backend reuse

    client = CourtListenerClient()
    inserted = 0
    try:
        for hit in client.search(court=court, q=query, page_size=limit):
            ops = hit.get("opinions") or []
            op_id = ops[0].get("id") if ops and isinstance(ops[0], dict) else None
            text = client.opinion_text(op_id) if op_id else (hit.get("snippet") or "")
            if not text:
                continue
            ext_id = str(hit.get("cluster_id") or hit.get("id"))
            citations = hit.get("citation") or hit.get("citations") or []
            if isinstance(citations, str):
                citations = [citations]
            new = _upsert_raw(
                db,
                source="courtlistener",
                external_id=ext_id,
                source_url=f"https://www.courtlistener.com/opinion/{hit.get('cluster_id') or ext_id}/",
                case_name=hit.get("caseName") or hit.get("case_name") or "Unknown",
                text=text,
                court=hit.get("court_id") or hit.get("court"),
                jurisdiction="federal",
                judge_name=hit.get("judge"),
                decided=hit.get("dateFiled"),
                meta={"citations": list(citations), "docket": hit.get("docketNumber"),
                      "license": "CourtListener terms"},
            )
            inserted += int(new)
        db.commit()
    finally:
        client.close()
    return inserted
