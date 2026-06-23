"""/graph/cluster and /graph/temporal — communities, statistical grouping, reasoning evolution."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from graphapp.analysis.clustering import detect_communities
from graphapp.analysis.propagation import statistical_grouping
from graphapp.analysis.temporal import reasoning_evolution
from graphapp.config import settings
from graphapp.ethics import GLOBAL_DISCLAIMER
from graphapp.neo4j_client import Neo4jClient, get_client
from graphapp.schemas import ClusterResult

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("/cluster", response_model=ClusterResult)
def cluster(
    topic: str | None = Query(None),
    n_groups: int | None = Query(None),
    client: Neo4jClient = Depends(get_client),
) -> ClusterResult:
    g = client.citation_digraph(topic=topic)
    communities = detect_communities(g)

    profiles = client.judge_topic_profiles()
    grouping = statistical_grouping(
        profiles,
        n_groups=n_groups or settings.n_groups,
        min_cases=settings.min_cases_per_judge,
    )
    return ClusterResult(
        communities=communities,
        statistical_grouping=grouping,
        disclaimer=GLOBAL_DISCLAIMER,
    )


@router.get("/temporal")
def temporal(client: Neo4jClient = Depends(get_client)) -> dict:
    result = reasoning_evolution(client)
    result["disclaimer"] = GLOBAL_DISCLAIMER
    return result
