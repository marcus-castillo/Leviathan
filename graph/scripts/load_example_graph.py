"""Apply the Neo4j schema and load the bundled example citation graph.

Usage:
    python -m scripts.load_example_graph
    python -m scripts.load_example_graph path/to/citations.jsonl
"""
from __future__ import annotations

import sys
from pathlib import Path

from graphapp.build.pipeline import build_from_jsonl
from graphapp.neo4j_client import get_client
from graphapp.schema import apply_schema

DEFAULT = Path(__file__).resolve().parent.parent / "graphapp" / "data" / "example_citations.jsonl"


def main(path: str | None = None) -> None:
    client = get_client()
    apply_schema(client)
    print("Schema applied.")
    stats = build_from_jsonl(client, Path(path) if path else DEFAULT)
    print(f"Loaded graph: {stats}")
    print("Neo4j browser: http://localhost:7474  ·  API: http://localhost:8001/docs")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
