"""Configuration for the graph service."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "leviathan_graph"

    # Optional: pull opinions/embeddings from the shared Postgres used by backend/corpus.
    database_url: str | None = None

    # Statistical-grouping defaults.
    n_groups: int = 2          # number of judge groups for KMeans (purely statistical)
    min_cases_per_judge: int = 3  # below this a judge is excluded from grouping

    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
