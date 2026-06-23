"""Load the bundled example dataset, then run the NLP pipeline + embeddings on everything.

Usage:
    python -m scripts.load_example_dataset
    python -m scripts.load_example_dataset path/to/other.jsonl
"""
from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import select

from app.db import SessionLocal, init_db
from app.ingestion.text_loader import ingest_text_file
from app.models import Opinion
from app.services import analyze_and_store

DEFAULT = Path(__file__).resolve().parent.parent / "data" / "example_opinions.jsonl"


def main(path: str | None = None) -> None:
    init_db()
    dataset = Path(path) if path else DEFAULT
    db = SessionLocal()
    try:
        n = ingest_text_file(db, dataset, source="example")
        print(f"Ingested {n} opinions from {dataset.name}.")

        opinions = db.execute(select(Opinion)).scalars().all()
        for i, op in enumerate(opinions, 1):
            analyze_and_store(db, op, with_embedding=True)
            if i % 5 == 0 or i == len(opinions):
                print(f"  analyzed {i}/{len(opinions)}")
        db.commit()
        print("Done. Visit http://localhost:8000/docs")
    finally:
        db.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
