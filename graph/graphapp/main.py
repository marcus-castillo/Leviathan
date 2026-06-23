"""Leviathan graph service FastAPI app."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from graphapp.api import routes_case, routes_cluster, routes_judge
from graphapp.config import settings
from graphapp.ethics import GLOBAL_DISCLAIMER

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("leviathan-graph")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        from graphapp.neo4j_client import get_client
        from graphapp.schema import apply_schema

        apply_schema(get_client())
        log.info("Neo4j schema applied.")
    except Exception as exc:  # pragma: no cover
        log.warning("Could not apply schema (is Neo4j up?): %s", exc)
    yield


app = FastAPI(
    title="Leviathan Graph",
    version="0.1.0",
    description="Citation-graph construction and influence analysis. " + GLOBAL_DISCLAIMER,
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

app.include_router(routes_case.router)
app.include_router(routes_judge.router)
app.include_router(routes_cluster.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.get("/ethics")
def ethics() -> dict:
    return {"disclaimer": GLOBAL_DISCLAIMER}
