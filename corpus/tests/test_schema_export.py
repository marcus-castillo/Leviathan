"""Tests for the parts that need neither a database nor the heavy backend models."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from levcorpus.export.writers import write_csv, write_jsonl
from levcorpus.extract import segmenter
from levcorpus.schema import (
    Annotations,
    CaseRecord,
    DecisionDirection,
    Outcome,
    make_judge_id,
    make_record_id,
    schema_field_names,
    text_hash,
)
from levcorpus.versioning.registry import _bump, _content_hash


def _sample_record() -> CaseRecord:
    text = "Plaintiff prevailed. We reverse."
    return CaseRecord(
        record_id=make_record_id("test", "x1", text),
        source="test",
        case_name="Doe v. Roe",
        judge="Hon. Jane Smith",
        judge_id=make_judge_id("jane smith"),
        text_sha256=text_hash(text),
        annotations=Annotations(
            outcome=Outcome.plaintiff,
            decision_direction=DecisionDirection.plaintiff_appellant,
        ),
    )


def test_record_ids_are_deterministic():
    a = make_record_id("courtlistener", "123", "hello")
    b = make_record_id("courtlistener", "123", "hello")
    c = make_record_id("courtlistener", "123", "world")
    assert a == b and a != c
    assert make_judge_id("jane smith") == make_judge_id("jane smith")
    assert make_judge_id(None) is None


def test_sentiment_proxy_is_flagged_weak():
    rec = _sample_record()
    assert "WEAK PROXY" in rec.annotations.sentiment_proxy_note


def test_schema_field_names_includes_nested():
    fields = schema_field_names()
    assert "annotations.decision_direction" in fields
    assert "parties.party_roles" in fields
    assert "embedding" in fields


def test_segmenter_buckets_sections():
    text = (
        "Doe v. Roe. Background. The parties dispute a contract. "
        "We must decide whether the contract is enforceable. "
        "Discussion. The terms are clear. "
        "Conclusion. Accordingly, we affirm. It is so ordered."
    )
    sec = segmenter.sections(text)
    assert sec["issue"]
    assert sec["disposition"]


def test_jsonl_and_csv_export(tmp_path: Path):
    rec = _sample_record().model_dump(mode="json")
    rec["embedding"] = [0.1, 0.2, 0.3]

    jl = tmp_path / "data.jsonl"
    assert write_jsonl([rec], jl) == 1
    loaded = json.loads(jl.read_text(encoding="utf-8").splitlines()[0])
    assert loaded["record_id"] == rec["record_id"]

    csv = tmp_path / "data.csv"
    assert write_csv([rec], csv) == 1
    header = csv.read_text(encoding="utf-8").splitlines()[0]
    # embedding vector dropped from CSV; replaced by a dim column; nested fields flattened.
    assert "embedding_dim" in header
    assert "annotations.outcome" in header


def test_parquet_export_handles_dynamic_party_roles(tmp_path: Path):
    pytest.importorskip("pyarrow")
    from levcorpus.export.writers import write_parquet

    recs = []
    for i, (a, b) in enumerate([("Alvarez", "United States"), ("Doe", "Acme Corp")]):
        rec = _sample_record().model_dump(mode="json")
        rec["embedding"] = [0.1, 0.2, 0.3] if i == 0 else None  # mixed null/list column
        rec["parties"]["party_roles"] = {a: "private", b: "government"}
        recs.append(rec)

    out = tmp_path / "data.parquet"
    assert write_parquet(recs, out) == 2

    import pandas as pd

    df = pd.read_parquet(out)
    assert len(df) == 2
    assert isinstance(df.iloc[0]["parties"], str)  # JSON-encoded, stable schema


def test_version_bump_and_hash():
    assert _bump("1.2.3", "major") == "2.0.0"
    assert _bump("1.2.3", "minor") == "1.3.0"
    assert _bump("1.2.3", "patch") == "1.2.4"
    h1 = _content_hash([{"record_id": "a", "text_sha256": "1"}])
    h2 = _content_hash([{"record_id": "a", "text_sha256": "1"}])
    assert h1 == h2
