"""Unit tests for CourtListener bulk-CSV parsing (stdlib only; no DB)."""
from __future__ import annotations

from scotusapp.corpus.courtlistener_bulk import (
    cluster_meta,
    court_docket_ids,
    iter_segment_rows,
    make_us_citation,
    opinion_type_to_kind,
    pick_text,
    strip_html,
    term_from_date,
    us_citations,
)


def test_opinion_type_to_kind():
    assert opinion_type_to_kind("020lead") == "majority"
    assert opinion_type_to_kind("025plurality") == "majority"
    assert opinion_type_to_kind("010combined") == "majority"
    assert opinion_type_to_kind("030concurrence") == "concurrence"
    assert opinion_type_to_kind("035concurrenceinpart") == "concurrence"
    assert opinion_type_to_kind("040dissent") == "dissent"
    assert opinion_type_to_kind("010combined", per_curiam=True) == "per_curiam"
    assert opinion_type_to_kind("060remittitur") is None


def test_make_us_citation_only_us_reports():
    assert make_us_citation("347", "U.S.", "483") == "347 U.S. 483"
    assert make_us_citation("123", "S. Ct.", "45") is None  # not U.S. Reports
    assert make_us_citation("347", "U.S.", None) is None


def test_text_helpers():
    assert strip_html("<p>Hello &amp; <b>world</b></p>") == "Hello & world"
    assert pick_text({"plain_text": "raw text"}) == "raw text"
    assert pick_text({"plain_text": "", "html": "<i>x</i>"}) == "x"
    assert term_from_date("1954-05-17") == 1954
    assert term_from_date("") is None


def _write(tmp_path, name, header, rows):
    p = tmp_path / name
    lines = [",".join(header)] + [",".join(r) for r in rows]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def test_scanners_filter_to_scotus(tmp_path):
    dockets = _write(tmp_path, "dockets.csv", ["id", "court_id", "case_name"],
                     [["1", "scotus", "Brown v. Board"], ["2", "ca9", "Other v. Thing"]])
    clusters = _write(tmp_path, "clusters.csv", ["id", "docket_id", "case_name", "date_filed", "scdb_id"],
                      [["10", "1", "Brown v. Board", "1954-05-17", "1953-001"],
                       ["20", "2", "Other v. Thing", "2001-01-01", ""]])
    citations = _write(tmp_path, "citations.csv", ["cluster_id", "volume", "reporter", "page"],
                       [["10", "347", "U.S.", "483"], ["10", "74", "S. Ct.", "686"],
                        ["20", "1", "F.3d", "1"]])
    opinions = _write(tmp_path, "opinions.csv",
                      ["id", "cluster_id", "type", "author_str", "per_curiam", "plain_text"],
                      [["100", "10", "020lead", "Warren", "f", "Majority body."],
                       ["101", "10", "040dissent", "Reed", "f", "Dissent body."],
                       ["102", "20", "020lead", "X", "f", "Ignored (not scotus)."]])

    dids = court_docket_ids(dockets)
    assert dids == {"1"}
    cmeta = cluster_meta(clusters, dids)
    assert set(cmeta) == {"10"} and cmeta["10"]["scdb_id"] == "1953-001"
    cites = us_citations(citations, set(cmeta))
    assert cites == {"10": "347 U.S. 483"}  # U.S. Reports preferred, S. Ct. ignored

    segs = list(iter_segment_rows(opinions, set(cmeta)))
    kinds = sorted((c, k) for c, k, _a, _t in segs)
    assert kinds == [("10", "dissent"), ("10", "majority")]
