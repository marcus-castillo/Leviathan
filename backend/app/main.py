"""Leviathan FastAPI application entry point."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_cases, routes_judges, routes_meta, routes_similar
from app.config import settings
from app.db import init_db
from app.ethics.guardrails import GLOBAL_DISCLAIMER

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("leviathan")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        log.info("Database initialized.")
    except Exception as exc:  # pragma: no cover
        log.warning("init_db failed (is Postgres up?): %s", exc)
    yield


app = FastAPI(
    title="Leviathan",
    version="0.1.0",
    description=(
        "Research-grade NLP for quantifying statistical disparities in judicial opinions. "
        + GLOBAL_DISCLAIMER
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_cases.router)
app.include_router(routes_judges.router)
app.include_router(routes_similar.router)
app.include_router(routes_meta.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.get("/ethics")
def ethics() -> dict:
    """Expose the global disclaimer for the frontend ethics banner."""
    return {
        "disclaimer": GLOBAL_DISCLAIMER,
        "min_sample_size": settings.min_sample_size,
        "confidence_level": settings.confidence_level,
    }
