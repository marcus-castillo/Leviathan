"""Load + segment the bundled example SCOTUS corpus.

Usage:
    python -m scripts.load_example_corpus [path.jsonl]
"""
from __future__ import annotations

import sys
from pathlib import Path

from scotusapp.corpus.loader import ingest_jsonl
from scotusapp.db import SessionLocal, init_db

DEFAULT = Path(__file__).resolve().parent.parent / "data" / "example_scotus.jsonl"


def main(path: str | None = None) -> None:
    init_db()
    db = SessionLocal()
    try:
        stats = ingest_jsonl(db, Path(path) if path else DEFAULT)
        print(f"Ingested + segmented: {stats}")
        print("Next: python -m scripts.build_justice_embeddings")
    finally:
        db.close()


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
