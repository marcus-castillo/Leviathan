"""Community detection over the citation graph (Louvain on the undirected projection)."""
from __future__ import annotations

import networkx as nx


def detect_communities(g: nx.DiGraph, resolution: float = 1.0, seed: int = 42) -> dict:
    """Return community membership + summaries.

    Communities are clusters of cases that cite each other densely. They are sensitive to the corpus
    and to ``resolution`` — they describe citation structure, not correctness or ideology.
    """
    if g.number_of_nodes() == 0:
        return {"membership": {}, "communities": []}

    undirected = g.to_undirected()
    communities = nx.community.louvain_communities(
        undirected, resolution=resolution, seed=seed
    )

    membership: dict[str, int] = {}
    summaries = []
    for idx, members in enumerate(sorted(communities, key=len, reverse=True)):
        members = list(members)
        for m in members:
            membership[m] = idx
        # Most-cited (highest in-degree) case as the community exemplar.
        exemplar = max(members, key=lambda n: g.in_degree(n)) if members else None
        summaries.append({
            "community": idx,
            "size": len(members),
            "exemplar": exemplar,
            "exemplar_name": g.nodes[exemplar].get("case_name") if exemplar else None,
            "members": members,
        })
    return {"membership": membership, "communities": summaries,
            "modularity": round(nx.community.modularity(undirected, communities), 4)}
