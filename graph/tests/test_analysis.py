"""Tests for the citation parser and the NetworkX/sklearn analytics (no Neo4j required)."""
from __future__ import annotations

import networkx as nx

from graphapp.analysis.clustering import detect_communities
from graphapp.analysis.influence import aggregate_judge_influence, compute_case_influence, influence_paths
from graphapp.analysis.propagation import statistical_grouping
from graphapp.build.citation_parser import classify_treatment, extract_citation_contexts


# --------------------------------------------------------------------------- #
# Citation parser
# --------------------------------------------------------------------------- #
def test_classify_treatment_signals():
    assert classify_treatment("We overrule our prior decision in Smith.") == "OVERRULES"
    assert classify_treatment("That case is distinguishable on its facts.") == "DISTINGUISHES"
    assert classify_treatment("We follow the reasoning of the panel.") == "FOLLOWS"
    assert classify_treatment("See generally the discussion above.") == "CITES"


def test_extract_citation_contexts_picks_strongest():
    text = (
        "We discussed Terry v. Ohio at length. "
        "We follow Chevron U.S.A. Inc. v. NRDC in resolving the question. "
        "The Government relies on Roe v. Wade, but that case is distinguishable here."
    )
    ctxs = {c["citation"]: c["treatment"] for c in extract_citation_contexts(text)}
    assert any("Chevron" in k for k in ctxs)
    assert any(v == "FOLLOWS" for v in ctxs.values())
    assert any(v == "DISTINGUISHES" for v in ctxs.values())


# --------------------------------------------------------------------------- #
# Influence
# --------------------------------------------------------------------------- #
def _toy_graph() -> nx.DiGraph:
    g = nx.DiGraph()
    # A landmark cited by everyone; edges point citing -> cited.
    for n, j in [("landmark", "j1"), ("a", "j2"), ("b", "j2"), ("c", "j3")]:
        g.add_node(n, case_name=n, judge_id=j)
    g.add_edge("a", "landmark", rel="FOLLOWS")
    g.add_edge("b", "landmark", rel="FOLLOWS")
    g.add_edge("c", "landmark", rel="CITES")
    g.add_edge("c", "a", rel="CITES")
    return g


def test_case_influence_landmark_is_most_cited():
    inf = compute_case_influence(_toy_graph())
    assert inf["landmark"]["cited_by"] == 3
    assert inf["landmark"]["pagerank"] >= inf["a"]["pagerank"]


def test_judge_influence_aggregates():
    agg = aggregate_judge_influence(_toy_graph())
    assert agg["j1"]["citation_influence"] == 3  # landmark cited 3x
    assert agg["j1"]["authored_cases"] == 1


def test_influence_paths_from_landmark():
    paths = influence_paths(_toy_graph(), "landmark")
    assert all(p[0] == "landmark" for p in paths)
    assert any(len(p) >= 2 for p in paths)


# --------------------------------------------------------------------------- #
# Clustering & statistical grouping
# --------------------------------------------------------------------------- #
def test_communities_detected():
    g = _toy_graph()
    res = detect_communities(g)
    assert set(res["membership"]) == set(g.nodes)
    assert res["communities"]


def test_statistical_grouping_is_neutral_and_caveated():
    profiles = {
        "j1": {"_name": "A", "immigration": 5, "habeas": 1},
        "j2": {"_name": "B", "immigration": 6},
        "j3": {"_name": "C", "tax": 4, "administrative": 3},
        "j4": {"_name": "D", "tax": 5},
    }
    res = statistical_grouping(profiles, n_groups=2, min_cases=3)
    assert len(res["groups"]) == 2
    labels = [grp["group"] for grp in res["groups"]]
    assert all(l.startswith("Group ") for l in labels)  # neutral labels, no ideology
    assert "not" in res["disclaimer"].lower() and "ideolog" in res["disclaimer"].lower()


def test_statistical_grouping_refuses_thin_data():
    res = statistical_grouping({"j1": {"_name": "A", "tax": 1}}, n_groups=2, min_cases=3)
    assert res["groups"] == []
