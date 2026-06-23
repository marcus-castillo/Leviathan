"""Influence / centrality analysis over a case citation DiGraph.

All functions take a ``networkx.DiGraph`` (edge attr ``rel`` ∈ CITES/OVERRULES/FOLLOWS/DISTINGUISHES,
node attr ``judge_id``), so they are unit-testable without Neo4j. Edge direction is citing→cited, so a
case's *in-degree* = how often it is cited (its authority).
"""
from __future__ import annotations

import networkx as nx


def compute_case_influence(g: nx.DiGraph) -> dict[str, dict]:
    """Per-case centrality.

    Edges point citing→cited, so on the original graph PageRank already flows *toward* authorities:
    a case that many (important) cases cite accumulates rank. A landmark precedent therefore scores
    highest.
    """
    if g.number_of_nodes() == 0:
        return {}

    try:
        pagerank = nx.pagerank(g, alpha=0.85)
    except nx.PowerIterationFailedConvergence:  # pragma: no cover
        pagerank = {n: 0.0 for n in g.nodes}

    betweenness = nx.betweenness_centrality(g) if g.number_of_nodes() > 2 else {n: 0.0 for n in g.nodes}

    out: dict[str, dict] = {}
    for n in g.nodes:
        out[n] = {
            "case_name": g.nodes[n].get("case_name"),
            "judge_id": g.nodes[n].get("judge_id"),
            "cited_by": g.in_degree(n),     # authority
            "cites": g.out_degree(n),
            "pagerank": round(pagerank.get(n, 0.0), 6),
            "betweenness": round(betweenness.get(n, 0.0), 6),
        }
    return out


def aggregate_judge_influence(g: nx.DiGraph) -> dict[str, dict]:
    """Roll case influence up to authoring judges.

    citation_influence = total times a judge's authored opinions are cited by others.
    """
    case_inf = compute_case_influence(g)
    judges: dict[str, dict] = {}
    for node, m in case_inf.items():
        jid = m.get("judge_id")
        if not jid:
            continue
        agg = judges.setdefault(jid, {"authored_cases": 0, "citation_influence": 0,
                                      "pagerank_sum": 0.0, "betweenness_sum": 0.0})
        agg["authored_cases"] += 1
        agg["citation_influence"] += m["cited_by"]
        agg["pagerank_sum"] += m["pagerank"]
        agg["betweenness_sum"] += m["betweenness"]
    for jid, agg in judges.items():
        n = max(agg["authored_cases"], 1)
        agg["pagerank_mean"] = round(agg["pagerank_sum"] / n, 6)
        agg["betweenness_mean"] = round(agg["betweenness_sum"] / n, 6)
        del agg["pagerank_sum"], agg["betweenness_sum"]
    return judges


def influence_paths(g: nx.DiGraph, source: str, max_paths: int = 10,
                    cutoff: int = 4) -> list[list[str]]:
    """Citation chains starting at ``source`` (how this case's authority propagates outward).

    Returns simple paths along reversed edges (source ← citing cases ← ...), truncated for display.
    """
    if source not in g:
        return []
    rev = g.reverse(copy=True)
    paths: list[list[str]] = []
    # Reachable nodes that cite (transitively) the source.
    for target in nx.descendants(rev, source):
        for p in nx.all_simple_paths(rev, source, target, cutoff=cutoff):
            paths.append(p)
            if len(paths) >= max_paths:
                return paths
    return paths
