"""Neo4j schema: uniqueness constraints + indexes. Idempotent."""
from __future__ import annotations

CONSTRAINTS = [
    "CREATE CONSTRAINT case_id IF NOT EXISTS FOR (c:Case) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT judge_id IF NOT EXISTS FOR (j:Judge) REQUIRE j.judge_id IS UNIQUE",
    "CREATE CONSTRAINT court_slug IF NOT EXISTS FOR (ct:Court) REQUIRE ct.slug IS UNIQUE",
    "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:LegalTopic) REQUIRE t.name IS UNIQUE",
]

INDEXES = [
    "CREATE INDEX case_decided IF NOT EXISTS FOR (c:Case) ON (c.decided)",
    "CREATE INDEX case_court IF NOT EXISTS FOR (c:Case) ON (c.court)",
]


def apply_schema(client) -> None:
    for stmt in CONSTRAINTS + INDEXES:
        client.write(stmt)
