"""Compute influence metrics and write them back onto Case/Judge nodes.

Lets the Neo4j browser and downstream queries use precomputed centrality (e.g. node sizing) without
recomputing per request.

Usage:
    python -m scripts.compute_metrics
"""
from __future__ import annotations

from graphapp.analysis.influence import aggregate_judge_influence, compute_case_influence
from graphapp.neo4j_client import get_client


def main() -> None:
    client = get_client()
    g = client.citation_digraph()

    case_inf = compute_case_influence(g)
    for cid, m in case_inf.items():
        client.write(
            "MATCH (c:Case {id: $id}) SET c.pagerank = $pr, c.cited_by = $cb, c.betweenness = $bt",
            id=cid, pr=m["pagerank"], cb=m["cited_by"], bt=m["betweenness"],
        )

    judge_inf = aggregate_judge_influence(g)
    for jid, m in judge_inf.items():
        client.write(
            "MATCH (j:Judge {judge_id: $id}) "
            "SET j.citation_influence = $ci, j.authored_cases = $ac, j.pagerank_mean = $pm",
            id=jid, ci=m["citation_influence"], ac=m["authored_cases"], pm=m["pagerank_mean"],
        )

    print(f"Wrote metrics for {len(case_inf)} cases and {len(judge_inf)} judges.")


if __name__ == "__main__":
    main()
