"""Shared ingestion helpers: normalize metadata and upsert opinions idempotently."""
from __future__ import annotations

import re
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Court, Judge, Opinion


def normalize_judge_name(name: str) -> str:
    name = re.sub(r"\b(Hon\.?|Judge|Justice|Chief)\b", "", name, flags=re.IGNORECASE)
    name = re.sub(r"[^A-Za-z\s.\-]", "", name)
    return re.sub(r"\s+", " ", name).strip().lower()


def get_or_create_judge(db: Session, name: str | None) -> Judge | None:
    if not name:
        return None
    norm = normalize_judge_name(name)
    if not norm:
        return None
    judge = db.execute(select(Judge).where(Judge.normalized_name == norm)).scalar_one_or_none()
    if judge is None:
        judge = Judge(normalized_name=norm, display_name=name.strip())
        db.add(judge)
        db.flush()
    return judge


def get_or_create_court(db: Session, slug: str | None, name: str | None = None) -> Court | None:
    if not slug:
        return None
    slug = slug.strip().lower()
    court = db.execute(select(Court).where(Court.slug == slug)).scalar_one_or_none()
    if court is None:
        court = Court(slug=slug, name=name or slug, jurisdiction="federal")
        db.add(court)
        db.flush()
    return court


def upsert_opinion(
    db: Session,
    *,
    case_name: str,
    text: str,
    judge_name: str | None = None,
    court: str | None = None,
    decided: date | None = None,
    case_type: str | None = None,
    citations: list[str] | None = None,
    source: str = "manual",
    external_id: str | None = None,
    extra: dict | None = None,
) -> Opinion:
    """Insert or update an opinion keyed on (source, external_id) when external_id is present."""
    existing = None
    if external_id:
        existing = db.execute(
            select(Opinion).where(Opinion.source == source, Opinion.external_id == external_id)
        ).scalar_one_or_none()

    judge = get_or_create_judge(db, judge_name)
    court_obj = get_or_create_court(db, court)
    meta = dict(extra or {})
    meta["citations"] = citations or meta.get("citations", [])

    if existing:
        existing.case_name = case_name
        existing.text = text
        existing.decided = decided
        existing.case_type = case_type
        existing.judge = judge
        existing.court = court_obj
        existing.extra = meta
        db.flush()
        return existing

    opinion = Opinion(
        source=source,
        external_id=external_id,
        case_name=case_name,
        text=text,
        decided=decided,
        case_type=case_type,
        judge=judge,
        court=court_obj,
        extra=meta,
    )
    db.add(opinion)
    db.flush()
    return opinion
