"""Configuration + path bootstrap for levcorpus.

Side effect on import: prepend the sibling ``backend/`` dir to ``sys.path`` so ``import app...`` works
when running from the monorepo. Override locations via environment variables.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(os.getenv("LEVCORPUS_BACKEND_DIR", REPO_ROOT / "backend"))

if BACKEND_DIR.exists() and str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://leviathan:leviathan@localhost:5432/leviathan",
)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Where versioned dataset artifacts are written.
DATASET_DIR = Path(os.getenv("CORPUS_DATASET_DIR", REPO_ROOT / "corpus" / "dataset"))

# CourtListener (reuses backend client; token optional).
COURTLISTENER_API_TOKEN = os.getenv("COURTLISTENER_API_TOKEN")


def resolved() -> dict:
    """Snapshot of config for reproducibility logs (secrets redacted)."""
    return {
        "database_url": _redact(DATABASE_URL),
        "embedding_model": EMBEDDING_MODEL,
        "dataset_dir": str(DATASET_DIR),
        "backend_dir": str(BACKEND_DIR),
        "courtlistener_token_set": bool(COURTLISTENER_API_TOKEN),
    }


def _redact(url: str) -> str:
    # Hide password in postgresql://user:pass@host/db
    import re

    return re.sub(r"://([^:/]+):([^@]+)@", r"://\1:***@", url)
