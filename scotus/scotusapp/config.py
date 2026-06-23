"""Config + path bootstrap. Importing prepends the sibling backend/ dir to sys.path so the
sentence-transformer encoder (app.embeddings) can be reused for justice embeddings."""
from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
for _candidate in (REPO_ROOT / "backend", Path("/app/backend")):
    if _candidate.exists() and str(_candidate) not in sys.path:
        sys.path.insert(0, str(_candidate))
        break


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://leviathan:leviathan@localhost:5432/leviathan"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Analysis defaults
    n_topics: int = 8
    n_justice_clusters: int = 3
    min_segments_per_justice: int = 3
    lexical_top_k: int = 25

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
