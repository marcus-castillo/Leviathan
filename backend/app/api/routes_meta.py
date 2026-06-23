"""Listing / aggregate endpoints that power the dashboard (judges, courts, corpus stats, trends)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, extract, func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Analysis, Court, Judge, Opinion

router = APIRouter(tags=["meta"])


@router.get("/judges")
def list_judges(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Judge.id, Judge.display_name, func.count(Opinion.id).label("n"))
        .outerjoin(Opinion, Opinion.judge_id == Judge.id)
        .group_by(Judge.id)
        .order_by(func.count(Opinion.id).desc())
    ).all()
    return [{"id": r.id, "display_name": r.display_name, "n_opinions": r.n} for r in rows]


@router.get("/courts")
def list_courts(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.execute(
        select(Court.id, Court.slug, Court.name, func.count(Opinion.id).label("n"))
        .outerjoin(Opinion, Opinion.court_id == Court.id)
        .group_by(Court.id)
        .order_by(func.count(Opinion.id).desc())
    ).all()
    return [{"id": r.id, "slug": r.slug, "name": r.name, "n_opinions": r.n} for r in rows]


@router.get("/stats")
def corpus_stats(db: Session = Depends(get_db)) -> dict:
    n_op = db.execute(select(func.count(Opinion.id))).scalar_one()
    n_an = db.execute(select(func.count(Analysis.id))).scalar_one()
    n_j = db.execute(select(func.count(Judge.id))).scalar_one()
    n_c = db.execute(select(func.count(Court.id))).scalar_one()
    return {"opinions": n_op, "analyzed": n_an, "judges": n_j, "courts": n_c}


@router.get("/courts/{court_id}/outcomes")
def court_outcomes(court_id: int, db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        select(Analysis.outcome, func.count())
        .join(Opinion, Opinion.id == Analysis.opinion_id)
        .where(Opinion.court_id == court_id)
        .group_by(Analysis.outcome)
    ).all()
    return {str(o): c for o, c in rows}


@router.get("/trends/plaintiff-rate")
def plaintiff_rate_trend(
    judge_id: int | None = Query(None),
    court_id: int | None = Query(None),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Plaintiff-favoring rate by year — powers the temporal-trend chart."""
    year = extract("year", Opinion.decided).label("year")
    stmt = (
        select(
            year,
            func.count().label("n"),
            func.sum(case((Analysis.outcome == "plaintiff", 1), else_=0)).label("p"),
        )
        .join(Opinion, Opinion.id == Analysis.opinion_id)
        .where(Opinion.decided.isnot(None))
        .where(Analysis.outcome.in_(["plaintiff", "defendant"]))
        .group_by(year)
        .order_by(year)
    )
    if judge_id:
        stmt = stmt.where(Opinion.judge_id == judge_id)
    if court_id:
        stmt = stmt.where(Opinion.court_id == court_id)

    out = []
    for r in db.execute(stmt).all():
        if r.year is None or not r.n:
            continue
        out.append({"year": int(r.year), "n": int(r.n),
                    "plaintiff_rate": round((r.p or 0) / r.n, 4)})
    return out
