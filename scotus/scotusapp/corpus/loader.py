"""Load SCOTUS opinions into the corpus, segmenting each into majority/concurrence/dissent.

Accepts records with either a full ``text`` (segmented automatically) or pre-split ``segments``.
A real deployment would page the CourtListener SCOTUS endpoint; the example loader reads JSONL.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from scotusapp.db import Case, Justice, OpinionSegment
from scotusapp.segmentation import segment_opinion


def _justice_slug(name: str) -> str:
    return re.sub(r"[^a-z]+", "-", name.lower()).strip("-")


def _get_or_create_justice(db: Session, name: str | None) -> Justice | None:
    if not name:
        return None
    slug = _justice_slug(name)
    if not slug:
        return None
    j = db.execute(select(Justice).where(Justice.slug == slug)).scalar_one_or_none()
    if j is None:
        j = Justice(slug=slug, name=name.strip())
        db.add(j)
        db.flush()
    return j


def ingest_records(db: Session, records: list[dict]) -> dict:
    stats = {"cases": 0, "segments": 0, "justices": 0}

    for rec in records:
        ext = rec.get("external_id") or rec.get("name")
        case = db.execute(select(Case).where(Case.external_id == ext)).scalar_one_or_none()
        if case is None:
            case = Case(external_id=ext)
            db.add(case)
        case.name = rec.get("name", ext)
        case.term = rec.get("term")
        case.citation = rec.get("citation")
        case.decided = rec.get("decided")
        case.extra = {k: v for k, v in rec.items()
                      if k not in {"external_id", "name", "term", "citation", "decided",
                                   "text", "segments"}}
        db.flush()
        stats["cases"] += 1

        # Replace existing segments for idempotency.
        for old in list(case.segments):
            db.delete(old)
        db.flush()

        if rec.get("segments"):
            raw_segments = [(s["kind"], s.get("author"), s["text"]) for s in rec["segments"]]
        else:
            raw_segments = [(s.kind, s.author, s.text) for s in segment_opinion(rec.get("text", ""))]

        seen_justices: set[int] = set()
        for kind, author, body in raw_segments:
            justice = _get_or_create_justice(db, author)
            if justice:
                seen_justices.add(justice.id)
            db.add(OpinionSegment(
                case_id=case.id, justice_id=justice.id if justice else None,
                kind=kind, author_name=author, text=body,
            ))
            stats["segments"] += 1
        stats["justices"] += len(seen_justices)

    db.commit()
    return stats


def ingest_jsonl(db: Session, path: str | Path) -> dict:
    records = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return ingest_records(db, records)
