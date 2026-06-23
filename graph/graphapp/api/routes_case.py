"""/graph/case/{id} and /graph/network — ego-networks and the explorer feed."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from graphapp.analysis.influence import compute_case_influence
from graphapp.ethics import GLOBAL_DISCLAIMER
from graphapp.neo4j_client import Neo4jClient, get_client
from graphapp.schemas import CaseGraph, GraphEdge, GraphNode, GraphPayload

router = APIRouter(prefix="/graph", tags=["graph"])

_EGO_CYPHER = """
MATCH (c:Case {id: $id})
OPTIONAL MATCH (c)-[r1:CITES|OVERRULES|FOLLOWS|DISTINGUISHES]->(out:Case)
OPTIONAL MATCH (in:Case)-[r2:CITES|OVERRULES|FOLLOWS|DISTINGUISHES]->(c)
OPTIONAL MATCH (c)-[:AUTHORED_BY]->(j:Judge)
RETURN c, j,
       collect(DISTINCT {n: out, rel: type(r1)}) AS outgoing,
       collect(DISTINCT {n: in, rel: type(r2)}) AS incoming
"""


def _case_node(props: dict) -> GraphNode:
    return GraphNode(id=props["id"], label="Case", name=props.get("case_name"),
                     attrs={k: v for k, v in props.items() if k not in ("id", "case_name")})


@router.get("/case/{case_id}", response_model=CaseGraph)
def case_graph(case_id: str, client: Neo4jClient = Depends(get_client)) -> CaseGraph:
    rows = client.run(_EGO_CYPHER, id=case_id)
    if not rows or rows[0]["c"] is None:
        raise HTTPException(404, "Case not found")
    row = rows[0]

    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    center = _case_node(row["c"])
    nodes[center.id] = center

    if row.get("j"):
        j = row["j"]
        nodes[j["judge_id"]] = GraphNode(id=j["judge_id"], label="Judge", name=j.get("display_name"))
        edges.append(GraphEdge(source=center.id, target=j["judge_id"], rel="AUTHORED_BY"))

    for item in row["outgoing"]:
        if item["n"] is None:
            continue
        node = _case_node(item["n"])
        nodes[node.id] = node
        edges.append(GraphEdge(source=center.id, target=node.id, rel=item["rel"]))
    for item in row["incoming"]:
        if item["n"] is None:
            continue
        node = _case_node(item["n"])
        nodes[node.id] = node
        edges.append(GraphEdge(source=node.id, target=center.id, rel=item["rel"]))

    return CaseGraph(
        focus=case_id,
        nodes=list(nodes.values()),
        edges=edges,
        disclaimer=GLOBAL_DISCLAIMER,
    )


@router.get("/network", response_model=GraphPayload)
def network(
    topic: str | None = Query(None),
    limit: int = Query(300, le=2000),
    client: Neo4jClient = Depends(get_client),
) -> GraphPayload:
    """Sampled case-to-case network for the zoomable explorer, with PageRank for node sizing."""
    g = client.citation_digraph(topic=topic)
    influence = compute_case_influence(g)

    nodes = [
        GraphNode(
            id=n, label="Case",
            name=g.nodes[n].get("case_name"),
            attrs={"pagerank": influence.get(n, {}).get("pagerank", 0.0),
                   "cited_by": influence.get(n, {}).get("cited_by", 0),
                   "judge_id": g.nodes[n].get("judge_id"),
                   "decided": g.nodes[n].get("decided")},
        )
        for n in list(g.nodes)[:limit]
    ]
    keep = {node.id for node in nodes}
    edges = [
        GraphEdge(source=u, target=v, rel=d.get("rel", "CITES"))
        for u, v, d in g.edges(data=True)
        if u in keep and v in keep
    ]
    return GraphPayload(nodes=nodes, edges=edges, disclaimer=GLOBAL_DISCLAIMER)
