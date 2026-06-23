"""Leviathan SCOTUS research platform FastAPI app."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from scotusapp.api import routes_analysis, routes_corpus, routes_justice
from scotusapp.config import settings
from scotusapp.ethics import GLOBAL_DISCLAIMER

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("leviathan-scotus")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from scotusapp.db import init_db

        init_db()
        log.info("SCOTUS tables initialized.")
    except Exception as exc:  # pragma: no cover
        log.warning("init_db failed (is Postgres up?): %s", exc)
    yield


app = FastAPI(
    title="Leviathan SCOTUS",
    version="0.1.0",
    description="NLP research platform for Supreme Court opinions. " + GLOBAL_DISCLAIMER,
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(routes_corpus.router)
app.include_router(routes_analysis.router)
app.include_router(routes_justice.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.get("/ethics")
def ethics() -> dict:
    return {"disclaimer": GLOBAL_DISCLAIMER}
