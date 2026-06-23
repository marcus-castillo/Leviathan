"""Ingest raw federal-decision text files with a small metadata sidecar.

Two supported forms:
  * a ``.txt`` opinion plus an optional ``.json`` sidecar of the same stem holding metadata;
  * a ``.jsonl`` file where each line is ``{case_name, text, judge_name, court, decided, ...}``.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

from app.ingestion.base import upsert_opinion
from app.nlp.issues import tag_issues


def _coerce_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _ingest_record(db: Session, rec: dict, source: str) -> None:
    text = rec["text"]
    case_type = rec.get("case_type") or (tag_issues(text) or ["unknown"])[0]
    upsert_opinion(
        db,
        case_name=rec.get("case_name", "Unknown"),
        text=text,
        judge_name=rec.get("judge_name") or rec.get("judge"),
        court=rec.get("court"),
        decided=_coerce_date(rec.get("decided")),
        case_type=case_type,
        citations=rec.get("citations", []),
        source=source,
        external_id=rec.get("external_id"),
        extra={k: v for k, v in rec.items()
               if k not in {"case_name", "text", "judge_name", "judge", "court",
                            "decided", "case_type", "citations", "external_id"}},
    )


def ingest_text_file(db: Session, path: str | Path, source: str = "text") -> int:
    """Ingest a .txt, .jsonl, or .json file. Returns number of opinions ingested."""
    path = Path(path)
    count = 0

    if path.suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            _ingest_record(db, json.loads(line), source)
            count += 1
    elif path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data if isinstance(data, list) else [data]
        for rec in records:
            _ingest_record(db, rec, source)
            count += 1
    else:  # plain text + optional sidecar
        text = path.read_text(encoding="utf-8")
        sidecar = path.with_suffix(".json")
        meta = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
        meta.setdefault("case_name", path.stem)
        meta["text"] = text
        meta.setdefault("external_id", path.stem)
        _ingest_record(db, meta, source)
        count = 1

    db.commit()
    return count
