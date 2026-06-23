"""Thin Neo4j driver wrapper + helpers to hydrate NetworkX graphs from Cypher."""
from __future__ import annotations

from functools import lru_cache

import networkx as nx
from neo4j import GraphDatabase

from graphapp.config import settings

# Case-to-case treatment relationship types.
CITATION_RELS = ["CITES", "OVERRULES", "FOLLOWS", "DISTINGUISHES"]


class Neo4jClient:
    def __init__(self, uri: str | None = None, user: str | None = None, password: str | None = None):
        self._driver = GraphDatabase.driver(
            uri or settings.neo4j_uri,
            auth=(user or settings.neo4j_user, password or settings.neo4j_password),
        )

    def close(self) -> None:
        self._driver.close()

    def run(self, cypher: str, **params) -> list[dict]:
        with self._driver.session() as session:
            return [r.data() for r in session.run(cypher, **params)]

    def write(self, cypher: str, **params) -> None:
        with self._driver.session() as session:
            session.run(cypher, **params)

    # ------------------------------------------------------------------ #
    # Graph hydration
    # ------------------------------------------------------------------ #
    def citation_digraph(self, topic: str | None = None) -> nx.DiGraph:
        """Directed graph of Case→Case treatment edges, with node + edge attributes."""
        rel_filter = "|".join(CITATION_RELS)
        cypher = f"""
        MATCH (a:Case)-[r:{rel_filter}]->(b:Case)
        {"WHERE EXISTS {{ MATCH (a)-[:ABOUT_TOPIC]->(:LegalTopic {{name: $topic}}) }}" if topic else ""}
        OPTIONAL MATCH (a)-[:AUTHORED_BY]->(ja:Judge)
        OPTIONAL MATCH (b)-[:AUTHORED_BY]->(jb:Judge)
        RETURN a.id AS src, b.id AS dst, type(r) AS rel,
               a.case_name AS src_name, b.case_name AS dst_name,
               a.decided AS src_decided, b.decided AS dst_decided,
               ja.judge_id AS src_judge, jb.judge_id AS dst_judge
        """
        g = nx.DiGraph()
        for row in self.run(cypher, topic=topic):
            g.add_node(row["src"], case_name=row["src_name"], decided=row["src_decided"],
                       judge_id=row["src_judge"])
            g.add_node(row["dst"], case_name=row["dst_name"], decided=row["dst_decided"],
                       judge_id=row["dst_judge"])
            # Weight negative/positive treatments; generic cite = 1.
            g.add_edge(row["src"], row["dst"], rel=row["rel"])
        return g

    def judge_topic_profiles(self) -> dict[str, dict[str, int]]:
        """For each judge: counts of authored cases per legal topic."""
        cypher = """
        MATCH (c:Case)-[:AUTHORED_BY]->(j:Judge)
        OPTIONAL MATCH (c)-[:ABOUT_TOPIC]->(t:LegalTopic)
        RETURN j.judge_id AS judge_id, j.display_name AS name,
               coalesce(t.name, 'unknown') AS topic, count(c) AS n
        """
        profiles: dict[str, dict[str, int]] = {}
        names: dict[str, str] = {}
        for row in self.run(cypher):
            jid = row["judge_id"]
            if not jid:
                continue
            names[jid] = row["name"]
            profiles.setdefault(jid, {"_name": row["name"]})
            profiles[jid][row["topic"]] = row["n"]
        return profiles


@lru_cache
def get_client() -> Neo4jClient:
    return Neo4jClient()
