"""Parse CourtListener bulk CSV dumps into SCOTUS case + opinion-segment records.

CourtListener publishes quarterly PostgreSQL ``COPY TO`` CSV snapshots
(https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/list.html?prefix=bulk-data/). The
relevant tables:

    search_docket          (id, court_id, case_name, ...)
    search_opinioncluster  (id, docket_id, case_name, date_filed, scdb_id, ...)
    search_opinion         (id, cluster_id, type, author_str, per_curiam, plain_text, html*, ...)
    search_citation        (cluster_id, volume, reporter, page, ...)

We filter to a court (default ``scotus``), group opinions by cluster, and map CourtListener's opinion
``type`` onto our segment kinds. Crucially, clusters carry ``scdb_id`` (= SCDB ``caseId``), giving a
direct, robust join to the Supreme Court Database without fragile citation matching.

This module is dependency-free (stdlib ``csv`` only) and does NOT touch the database, so its parsing
logic is unit-testable. The DB ingest lives in ``scripts/load_courtlistener_bulk.py``.
"""
from __future__ import annotations

import csv
import re
import sys
from collections.abc import Iterator
from pathlib import Path

# CourtListener stores very large text fields; raise the CSV field-size limit.
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))


# --------------------------------------------------------------------------- #
# Type / text / citation helpers (pure)
# --------------------------------------------------------------------------- #
def opinion_type_to_kind(type_str: str | None, per_curiam: bool = False) -> str | None:
    """Map a CourtListener opinion ``type`` to a segment kind, or None to skip.

    CL types include 010combined, 015unamimous, 020lead, 025plurality, 030concurrence,
    035concurrenceinpart, 040dissent, plus non-opinion types (addendum, remittitur, rehearing) which
    we skip.
    """
    t = (type_str or "").lower()
    if per_curiam or "percuriam" in t or "per_curiam" in t:
        return "per_curiam"
    if "dissent" in t:
        return "dissent"
    if "concur" in t:
        return "concurrence"
    if any(k in t for k in ("lead", "plurality", "unanim", "unamim", "combined",
                            "onthemerits", "majority")):
        return "majority"
    return None


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&#167;", "§"),
                    ("&nbsp;", " "), ("&quot;", '"'), ("&#39;", "'")):
        text = text.replace(ent, ch)
    return re.sub(r"\s+", " ", text).strip()


# Preference order for opinion text columns in the bulk dump.
_TEXT_COLUMNS = ["plain_text", "html_with_citations", "html_columbia", "html_lawbox", "html",
                 "xml_harvard"]


def pick_text(row: dict) -> str:
    if row.get("plain_text", "").strip():
        return row["plain_text"]
    for col in _TEXT_COLUMNS[1:]:
        if row.get(col, "").strip():
            return strip_html(row[col])
    return ""


def make_us_citation(volume: str | None, reporter: str | None, page: str | None) -> str | None:
    """Build a SCDB-style U.S. Reports citation, e.g. '347 U.S. 483'. Only for U.S. Reports."""
    if not (volume and page and reporter):
        return None
    if reporter.strip().upper().replace(" ", "") not in ("U.S.", "US"):
        return None
    return f"{volume.strip()} U.S. {page.strip()}"


def term_from_date(date_filed: str | None) -> int | None:
    if date_filed and len(date_filed) >= 4 and date_filed[:4].isdigit():
        return int(date_filed[:4])
    return None


# --------------------------------------------------------------------------- #
# CSV scanners (filter to a court; build small SCOTUS-only indexes)
# --------------------------------------------------------------------------- #
def _reader(path: str | Path):
    return csv.DictReader(open(path, encoding="utf-8", newline=""))


def court_docket_ids(dockets_csv: str | Path, court_id: str = "scotus") -> set[str]:
    return {row["id"] for row in _reader(dockets_csv) if row.get("court_id") == court_id}


def cluster_meta(clusters_csv: str | Path, docket_ids: set[str]) -> dict[str, dict]:
    """Return {cluster_id: {case_name, date_filed, scdb_id}} for clusters in the given dockets."""
    out: dict[str, dict] = {}
    for row in _reader(clusters_csv):
        if row.get("docket_id") in docket_ids:
            out[row["id"]] = {
                "case_name": row.get("case_name", ""),
                "date_filed": row.get("date_filed", ""),
                "scdb_id": (row.get("scdb_id") or "").strip() or None,
            }
    return out


def us_citations(citations_csv: str | Path, cluster_ids: set[str]) -> dict[str, str]:
    """Return {cluster_id: 'V U.S. P'} preferring U.S. Reports citations."""
    out: dict[str, str] = {}
    for row in _reader(citations_csv):
        cid = row.get("cluster_id")
        if cid not in cluster_ids or cid in out:
            continue
        cite = make_us_citation(row.get("volume"), row.get("reporter"), row.get("page"))
        if cite:
            out[cid] = cite
    return out


def iter_segment_rows(
    opinions_csv: str | Path, cluster_ids: set[str]
) -> Iterator[tuple[str, str, str | None, str]]:
    """Stream (cluster_id, kind, author, text) for opinions in the given clusters.

    Streaming (no accumulation) keeps memory bounded even though the opinions dump is large.
    """
    for row in _reader(opinions_csv):
        cid = row.get("cluster_id")
        if cid not in cluster_ids:
            continue
        per_curiam = str(row.get("per_curiam", "")).strip().lower() in ("t", "true", "1")
        kind = opinion_type_to_kind(row.get("type"), per_curiam=per_curiam)
        if kind is None:
            continue
        text = pick_text(row)
        if not text.strip():
            continue
        yield cid, kind, (row.get("author_str") or None), text
