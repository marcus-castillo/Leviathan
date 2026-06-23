"""Embed opinion segments and build per-justice style fingerprints.

Usage:
    python -m scripts.build_justice_embeddings
"""
from __future__ import annotations

from scotusapp.db import SessionLocal, init_db
from scotusapp.services import build_justice_fingerprints, embed_segments


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        n = embed_segments(db, only_missing=True)
        print(f"Embedded {n} segment(s).")
        j = build_justice_fingerprints(db)
        print(f"Built style fingerprints for {j} justice(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
