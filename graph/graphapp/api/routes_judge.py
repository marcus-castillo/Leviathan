"""/graph/judge/{id} — a judge's authored cases, influence scores, and influence paths."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from graphapp.analysis.influence import aggregate_judge_influence, influence_paths
from graphapp.ethics import GLOBAL_DISCLAIMER
from graphapp.neo4j_client import Neo4jClient, get_client
from graphapp.schemas import GraphEdge, GraphNode, JudgeGraph

router = APIRouter(prefix="/graph", tags=["graph"])

_JUDGE_CYPHER = """
MATCH (j:Judge {judge_id: $id})
OPTIONAL MATCH (c:Case)-[:AUTHORED_BY]->(j)
OPTIONAL MATCH (c)-[r:CITES|OVERRULES|FOLLOWS|DISTINGUISHES]->(cited:Case)
RETURN j, collect(DISTINCT c) AS cases,
       collect(DISTINCT {src: c.id, dst: cited.id, rel: type(r)}) AS edges
"""


@router.get("/judge/{judge_id}", response_model=JudgeGraph)
def judge_graph(
    judge_id: str,
    paths_from: str | None = Query(None, description="case id to trace influence paths from"),
    client: Neo4jClient = Depends(get_client),
) -> JudgeGraph:
    rows = client.run(_JUDGE_CYPHER, id=judge_id)
    if not rows or rows[0]["j"] is None:
        raise HTTPException(404, "Judge not found")
    row = rows[0]
    j = row["j"]

    nodes: dict[str, GraphNode] = {
        judge_id: GraphNode(id=judge_id, label="Judge", name=j.get("display_name"))
    }
    edges: list[GraphEdge] = []
    for c in row["cases"]:
        if not c:
            continue
        nodes[c["id"]] = GraphNode(id=c["id"], label="Case", name=c.get("case_name"),
                                   attrs={"decided": c.get("decided")})
        edges.append(GraphEdge(source=c["id"], target=judge_id, rel="AUTHORED_BY"))
    for e in row["edges"]:
        if not e or e["dst"] is None:
            continue
        nodes.setdefault(e["dst"], GraphNode(id=e["dst"], label="Case"))
        edges.append(GraphEdge(source=e["src"], target=e["dst"], rel=e["rel"]))

    # Influence scores from the full citation graph.
    g = client.citation_digraph()
    influence = aggregate_judge_influence(g).get(judge_id)
    paths = influence_paths(g, paths_from) if paths_from else []

    return JudgeGraph(
        judge_id=judge_id,
        nodes=list(nodes.values()),
        edges=edges,
        influence=influence,
        paths=paths,
        disclaimer=GLOBAL_DISCLAIMER,
    )
