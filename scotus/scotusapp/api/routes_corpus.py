"""/corpus/ingest — load + segment opinions."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from scotusapp.corpus.loader import ingest_records
from scotusapp.db import get_db
from scotusapp.ethics import GLOBAL_DISCLAIMER
from scotusapp.schemas import IngestResult

router = APIRouter(prefix="/corpus", tags=["corpus"])


class IngestIn(BaseModel):
    records: list[dict]


@router.post("/ingest", response_model=IngestResult)
def ingest(payload: IngestIn, db: Session = Depends(get_db)) -> IngestResult:
    stats = ingest_records(db, payload.records)
    return IngestResult(**stats, disclaimer=GLOBAL_DISCLAIMER)
