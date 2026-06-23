"""(Re)compute analyses + embeddings for any opinions missing them.

Useful after bulk ingestion that skipped analysis, or after changing the embedding model.

Usage:
    python -m scripts.build_embeddings [--all]
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.models import Analysis, Opinion
from app.services import analyze_and_store


def main(rebuild_all: bool = False) -> None:
    init_db()
    db = SessionLocal()
    try:
        stmt = select(Opinion)
        if not rebuild_all:
            stmt = stmt.outerjoin(Analysis, Analysis.opinion_id == Opinion.id).where(
                (Analysis.id.is_(None)) | (Analysis.embedding.is_(None))
            )
        opinions = db.execute(stmt).scalars().all()
        print(f"Computing embeddings for {len(opinions)} opinion(s)...")
        for i, op in enumerate(opinions, 1):
            analyze_and_store(db, op, with_embedding=True)
            if i % 10 == 0 or i == len(opinions):
                db.commit()
                print(f"  {i}/{len(opinions)}")
        db.commit()
        print("Embeddings up to date.")
    finally:
        db.close()


if __name__ == "__main__":
    main(rebuild_all="--all" in sys.argv)
