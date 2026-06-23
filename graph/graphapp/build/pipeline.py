"""Graph construction: MERGE Cases/Judges/Courts/Topics + typed citation edges into Neo4j.

Two entry points:
  * ``build_from_records`` — list of dicts (the canonical builder).
  * ``build_from_jsonl`` — convenience wrapper that reads a JSONL file.

Record shape (all but ``id``/``case_name`` optional)::

    {
      "id": "case-001",
      "case_name": "Alvarez v. United States",
      "judge": "Hon. Eleanor Marsh",
      "judge_id": "j_ab12...",          # optional; derived from name if absent
      "court": "ca9",
      "topics": ["immigration"],
      "decided": "2021-03-14",
      "decision_direction": "plaintiff_appellant_favored",
      "cites": [{"target": "scotus-cardoza", "treatment": "follows"}],
      "text": "..."                       # optional; if present and no `cites`, edges are parsed
    }
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from graphapp.build.citation_parser import extract_citation_contexts

# Treatment string (lowercase) -> Neo4j relationship type.
_REL = {"cites": "CITES", "overrules": "OVERRULES", "follows": "FOLLOWS",
        "distinguishes": "DISTINGUISHES"}


def _normalize_judge(name: str) -> str:
    name = re.sub(r"\b(Hon\.?|Judge|Justice|Chief)\b", "", name, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z\s.\-]", "", name)).strip().lower()


def _judge_id(name: str | None, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    if not name:
        return None
    return "j_" + hashlib.sha1(_normalize_judge(name).encode()).hexdigest()[:12]


_MERGE_CASE = """
MERGE (c:Case {id: $id})
SET c.case_name = $case_name, c.decided = $decided, c.court = $court,
    c.decision_direction = $decision_direction
"""

_MERGE_JUDGE = """
MERGE (j:Judge {judge_id: $judge_id})
SET j.display_name = coalesce($display_name, j.display_name)
WITH j
MATCH (c:Case {id: $case_id})
MERGE (c)-[:AUTHORED_BY]->(j)
"""

_MERGE_COURT = """
MERGE (ct:Court {slug: $slug})
SET ct.name = coalesce($name, ct.name), ct.jurisdiction = 'federal'
WITH ct
MATCH (c:Case {id: $case_id})
MERGE (c)-[:IN_COURT]->(ct)
"""

_MERGE_TOPIC = """
MERGE (t:LegalTopic {name: $name})
WITH t
MATCH (c:Case {id: $case_id})
MERGE (c)-[:ABOUT_TOPIC]->(t)
"""

# Cited target may not exist as a full case yet; MERGE a stub Case node by id.
_MERGE_EDGE_TMPL = """
MATCH (a:Case {{id: $src}})
MERGE (b:Case {{id: $dst}})
ON CREATE SET b.case_name = $dst_name, b.stub = true
MERGE (a)-[r:{rel}]->(b)
"""


def _target_id(target: str) -> str:
    """Stable id for a cited target given either an explicit id or a citation string."""
    if re.fullmatch(r"[a-z0-9][a-z0-9\-_]+", target):
        return target  # looks like an explicit node id
    return "cite-" + hashlib.sha1(target.lower().encode()).hexdigest()[:12]


def build_from_records(client, records: list[dict]) -> dict:
    stats = {"cases": 0, "judges": 0, "courts": 0, "topics": 0, "edges": 0}

    for rec in records:
        cid = rec["id"]
        client.write(
            _MERGE_CASE,
            id=cid,
            case_name=rec.get("case_name", cid),
            decided=rec.get("decided"),
            court=rec.get("court"),
            decision_direction=rec.get("decision_direction"),
        )
        stats["cases"] += 1

        jname = rec.get("judge")
        jid = _judge_id(jname, rec.get("judge_id"))
        if jid:
            client.write(_MERGE_JUDGE, judge_id=jid, display_name=jname, case_id=cid)
            stats["judges"] += 1

        if rec.get("court"):
            client.write(_MERGE_COURT, slug=rec["court"], name=rec.get("court_name"), case_id=cid)
            stats["courts"] += 1

        for topic in rec.get("topics", []):
            client.write(_MERGE_TOPIC, name=topic, case_id=cid)
            stats["topics"] += 1

        # Edges: explicit list preferred; otherwise parse from text.
        cites = rec.get("cites")
        if cites is None and rec.get("text"):
            cites = [
                {"target": ctx["citation"], "treatment": ctx["treatment"].lower()}
                for ctx in extract_citation_contexts(rec["text"])
            ]
        for edge in cites or []:
            rel = _REL.get((edge.get("treatment") or "cites").lower(), "CITES")
            dst = _target_id(edge["target"])
            client.write(
                _MERGE_EDGE_TMPL.format(rel=rel),
                src=cid, dst=dst, dst_name=edge.get("target"),
            )
            stats["edges"] += 1

    return stats


def build_from_jsonl(client, path: str | Path) -> dict:
    records = [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return build_from_records(client, records)
