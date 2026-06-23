"""Centralized configuration loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+psycopg://leviathan:leviathan@localhost:5432/leviathan"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    # NLP / models
    spacy_model: str = "en_core_web_sm"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    outcome_model_path: str | None = None

    # Ethics guardrails
    min_sample_size: int = 30
    confidence_level: float = 0.95
    fdr_alpha: float = 0.05

    # External
    courtlistener_api_token: str | None = None
    courtlistener_base_url: str = "https://www.courtlistener.com/api/rest/v4"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
