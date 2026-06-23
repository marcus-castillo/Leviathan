"""Temporal evolution of legal reasoning.

Queries Neo4j for per-year topic mix and the most-cited precedents per era, so the frontend can show
how citation patterns and topical emphasis shift over time. Descriptive only.
"""
from __future__ import annotations


def _year(decided: str | None) -> int | None:
    if not decided or len(decided) < 4 or not decided[:4].isdigit():
        return None
    return int(decided[:4])


def reasoning_evolution(client) -> dict:
    """Return per-year topic counts and top cited precedents per (5-year) era."""
    topic_rows = client.run(
        """
        MATCH (c:Case)-[:ABOUT_TOPIC]->(t:LegalTopic)
        WHERE c.decided IS NOT NULL
        RETURN c.decided AS decided, t.name AS topic
        """
    )
    by_year: dict[int, dict[str, int]] = {}
    for row in topic_rows:
        y = _year(row["decided"])
        if y is None:
            continue
        by_year.setdefault(y, {}).setdefault(row["topic"], 0)
        by_year[y][row["topic"]] += 1

    timeline = [
        {"year": y, "topics": topics, "total": sum(topics.values())}
        for y, topics in sorted(by_year.items())
    ]

    # Most-cited precedents per 5-year era (in-degree of cited cases).
    era_rows = client.run(
        """
        MATCH (citing:Case)-[r:CITES|FOLLOWS|OVERRULES|DISTINGUISHES]->(cited:Case)
        WHERE citing.decided IS NOT NULL
        RETURN citing.decided AS decided, cited.id AS cited_id,
               cited.case_name AS cited_name, count(*) AS n
        """
    )
    eras: dict[int, dict[str, dict]] = {}
    for row in era_rows:
        y = _year(row["decided"])
        if y is None:
            continue
        era = (y // 5) * 5
        bucket = eras.setdefault(era, {})
        ref = bucket.setdefault(row["cited_id"],
                                {"cited_id": row["cited_id"], "name": row["cited_name"], "count": 0})
        ref["count"] += row["n"]

    top_by_era = [
        {"era": f"{era}-{era + 4}",
         "top_precedents": sorted(refs.values(), key=lambda d: d["count"], reverse=True)[:5]}
        for era, refs in sorted(eras.items())
    ]

    return {
        "timeline": timeline,
        "top_precedents_by_era": top_by_era,
        "note": "Counts reflect corpus coverage, which is uneven across years; absence of data is not "
                "absence of activity.",
    }
