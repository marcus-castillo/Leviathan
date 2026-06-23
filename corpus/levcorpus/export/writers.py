"""Standardized export writers: JSONL, CSV, Parquet.

Records are plain dicts (``CaseRecord.model_dump(mode="json")``). The 384-d ``embedding`` array is kept
in JSONL and Parquet (native list column) but dropped from CSV — a flat tabular format where a long
float vector per row is unhelpful. CSV instead carries an ``embedding_dim`` column for sanity checks.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable


def write_jsonl(records: Iterable[dict], path: str | Path) -> int:
    path = Path(path)
    n = 0
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            n += 1
    return n


def _flatten_for_table(rec: dict) -> dict:
    """Flatten nested groups (parties, annotations) into dotted columns; drop the embedding."""
    flat: dict = {}
    for k, v in rec.items():
        if k == "embedding":
            flat["embedding_dim"] = len(v) if isinstance(v, list) else 0
            continue
        if isinstance(v, dict):
            for sk, sv in v.items():
                flat[f"{k}.{sk}"] = sv if not isinstance(sv, (list, dict)) else json.dumps(sv, default=str)
        elif isinstance(v, list):
            flat[k] = json.dumps(v, ensure_ascii=False, default=str)
        else:
            flat[k] = v
    return flat


def write_csv(records: Iterable[dict], path: str | Path) -> int:
    import pandas as pd

    rows = [_flatten_for_table(r) for r in records]
    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return len(df)


def _parquet_normalize(rec: dict) -> dict:
    """Make a record Arrow-friendly.

    ``parties`` contains ``party_roles``, a dict with *dynamic* keys (party names). Arrow would try to
    infer an unstable struct schema across rows, so we JSON-encode ``parties`` to a string. Fixed-key
    structs (``annotations``) and list columns (``embedding``, ``topic``, ``citations``) are left
    native so they stay queryable.
    """
    out = dict(rec)
    if isinstance(out.get("parties"), dict):
        out["parties"] = json.dumps(out["parties"], ensure_ascii=False, default=str)
    return out


def write_parquet(records: Iterable[dict], path: str | Path) -> int:
    import pandas as pd

    rows = [_parquet_normalize(r) for r in records]
    df = pd.DataFrame(rows)
    # pyarrow handles the list<float> embedding column and the fixed-key annotations struct.
    df.to_parquet(path, index=False, engine="pyarrow")
    return len(df)


WRITERS = {"jsonl": write_jsonl, "csv": write_csv, "parquet": write_parquet}
