"""Collect public-domain federal opinions from local files into the raw staging table.

Accepts a directory or single path of:
  * ``.txt``  (+ optional ``.json`` sidecar of the same stem for metadata)
  * ``.json`` (one record or a list)
  * ``.jsonl`` (one record per line)

Record fields: case_name, text, judge_name|judge, court, jurisdiction, decided, citations, parties,
external_id, source_url, license.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.orm import Session

from levcorpus.collect.courtlistener import _upsert_raw


def _ingest_record(db: Session, rec: dict, default_id: str) -> bool:
    meta = {k: v for k, v in rec.items()
            if k not in {"case_name", "text", "judge_name", "judge", "court",
                         "jurisdiction", "decided", "external_id", "source_url"}}
    meta.setdefault("license", "Public domain (U.S. government work)")
    return _upsert_raw(
        db,
        source="public-domain",
        external_id=rec.get("external_id") or default_id,
        source_url=rec.get("source_url"),
        case_name=rec.get("case_name", default_id),
        text=rec["text"],
        court=rec.get("court"),
        jurisdiction=rec.get("jurisdiction", "federal"),
        judge_name=rec.get("judge_name") or rec.get("judge"),
        decided=str(rec["decided"]) if rec.get("decided") else None,
        meta=meta,
    )


def collect_public_domain(db: Session, path: str | Path) -> int:
    path = Path(path)
    files: list[Path] = []
    if path.is_dir():
        files = sorted(p for p in path.rglob("*") if p.suffix in {".txt", ".json", ".jsonl"})
    else:
        files = [path]

    inserted = 0
    for f in files:
        if f.suffix == ".jsonl":
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines()):
                line = line.strip()
                if line:
                    inserted += int(_ingest_record(db, json.loads(line), f"{f.stem}-{i}"))
        elif f.suffix == ".json":
            data = json.loads(f.read_text(encoding="utf-8"))
            for i, rec in enumerate(data if isinstance(data, list) else [data]):
                inserted += int(_ingest_record(db, rec, f"{f.stem}-{i}"))
        elif f.suffix == ".txt":
            sidecar = f.with_suffix(".json")
            rec = json.loads(sidecar.read_text(encoding="utf-8")) if sidecar.exists() else {}
            rec["text"] = f.read_text(encoding="utf-8")
            rec.setdefault("case_name", f.stem)
            inserted += int(_ingest_record(db, rec, f.stem))
    db.commit()
    return inserted
