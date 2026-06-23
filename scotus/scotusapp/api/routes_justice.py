"""/justice/* and /similar-cases — justice profiles, style similarity map, cross-divide retrieval."""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from scotusapp.analysis.framing import justice_framing
from scotusapp.analysis.justice_embeddings import (
    nearest_justices,
    similarity_matrix,
    style_clusters,
)
from scotusapp.config import settings
from scotusapp.db import Case, Justice, OpinionSegment, get_db
from scotusapp.ethics import GLOBAL_DISCLAIMER, STYLE_CLUSTER_DISCLAIMER
from scotusapp.schemas import JusticeProfile, SimilarCasesResult, SimilarityMap
from scotusapp.similar import find_similar_cases

router = APIRouter(tags=["justice"])


def _justice_texts(db: Session) -> dict[str, list[str]]:
    rows = db.execute(
        select(Justice.slug, OpinionSegment.text)
        .join(OpinionSegment, OpinionSegment.justice_id == Justice.id)
    ).all()
    out: dict[str, list[str]] = defaultdict(list)
    for slug, text in rows:
        out[slug].append(text)
    return out


def _justice_vectors(db: Session) -> dict[str, list[float]]:
    rows = db.execute(select(Justice.slug, Justice.embedding)).all()
    return {slug: list(emb) for slug, emb in rows if emb is not None}


def _cluster_of(db: Session) -> dict[str, int]:
    """Map justice name -> style-cluster index (used to flag cross-divide similar cases)."""
    vectors = _justice_vectors(db)
    clusters = style_clusters(vectors, n_clusters=settings.n_justice_clusters)
    name_by_slug = {j.slug: j.name for j in db.execute(select(Justice)).scalars().all()}
    mapping: dict[str, int] = {}
    for i, c in enumerate(clusters.get("clusters", [])):
        for slug in c["justices"]:
            if slug in name_by_slug:
                mapping[name_by_slug[slug]] = i
    return mapping


@router.get("/justice/similarity", response_model=SimilarityMap)
def justice_similarity(db: Session = Depends(get_db)) -> SimilarityMap:
    vectors = _justice_vectors(db)
    sim = similarity_matrix(vectors)
    clusters = style_clusters(vectors, n_clusters=settings.n_justice_clusters)
    return SimilarityMap(
        justices=sim["justices"], matrix=sim["matrix"],
        clusters=clusters.get("clusters", []),
        disclaimer=GLOBAL_DISCLAIMER + " " + STYLE_CLUSTER_DISCLAIMER,
    )


@router.get("/justice/{slug}", response_model=JusticeProfile)
def justice_profile(slug: str, db: Session = Depends(get_db)) -> JusticeProfile:
    justice = db.execute(select(Justice).where(Justice.slug == slug)).scalar_one_or_none()
    if justice is None:
        raise HTTPException(404, "Justice not found")

    framing = justice_framing(_justice_texts(db), slug, top_k=settings.lexical_top_k)
    nearest = nearest_justices(_justice_vectors(db), slug)
    return JusticeProfile(
        slug=slug, name=justice.name, n_segments=justice.n_segments,
        distinctive_terms=framing.get("distinctive", []),
        nearest=nearest, disclaimer=GLOBAL_DISCLAIMER,
    )


class SimilarIn(BaseModel):
    case_id: int
    top_k: int = 10


@router.post("/similar-cases", response_model=SimilarCasesResult)
def similar_cases(payload: SimilarIn, db: Session = Depends(get_db)) -> SimilarCasesResult:
    case = db.get(Case, payload.case_id)
    if case is None:
        raise HTTPException(404, "Case not found")
    majority = next((s for s in case.segments if s.kind == "majority" and s.embedding is not None), None)
    if majority is None:
        raise HTTPException(409, "Query case has no embedded majority opinion. Run embeddings first.")

    results = find_similar_cases(
        db,
        query_vector=list(majority.embedding),
        exclude_case_id=case.id,
        style_cluster_of=_cluster_of(db),
        query_author=majority.author_name,
        top_k=payload.top_k,
    )
    return SimilarCasesResult(query_case=case.name, results=results, disclaimer=GLOBAL_DISCLAIMER)
