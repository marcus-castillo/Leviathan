"""Ingest a real SCOTUS corpus from CourtListener bulk CSV dumps.

Download the quarterly CSVs (courts/dockets/clusters/opinions/citations) from
https://com-courtlistener-storage.s3-us-west-2.amazonaws.com/list.html?prefix=bulk-data/ and pass
their paths. Opinions are grouped by cluster and segmented by CourtListener opinion type; each cluster
becomes one Case (with its scdb_id stored for a direct SCDB join).

Usage:
    python -m scripts.load_courtlistener_bulk \
        --dockets dockets.csv --clusters opinion-clusters.csv \
        --citations citations.csv --opinions opinions.csv

These CSVs are large; the loader streams the opinions file. Run build_justice_embeddings afterwards.
"""
from __future__ import annotations

import argparse

from scotusapp.corpus.courtlistener_bulk import (
    cluster_meta,
    court_docket_ids,
    iter_segment_rows,
    term_from_date,
    us_citations,
)
from scotusapp.db import Case, OpinionSegment, SessionLocal, init_db


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dockets", required=True)
    ap.add_argument("--clusters", required=True)
    ap.add_argument("--citations", required=True)
    ap.add_argument("--opinions", required=True)
    ap.add_argument("--court", default="scotus")
    args = ap.parse_args()

    init_db()

    print(f"Scanning dockets for court={args.court} ...")
    docket_ids = court_docket_ids(args.dockets, args.court)
    print(f"  {len(docket_ids)} dockets")

    clusters = cluster_meta(args.clusters, docket_ids)
    cluster_ids = set(clusters)
    print(f"  {len(cluster_ids)} clusters")

    cites = us_citations(args.citations, cluster_ids)
    print(f"  {len(cites)} clusters with a U.S. Reports citation")

    db = SessionLocal()
    n_cases = n_segments = 0
    case_id_by_cluster: dict[str, int] = {}
    try:
        # Create a Case per cluster up front (so segments can attach by cluster id).
        for cluster_id, meta in clusters.items():
            ext = f"cl-{cluster_id}"
            case = db.query(Case).filter(Case.external_id == ext).one_or_none()
            if case is None:
                case = Case(external_id=ext)
                db.add(case)
            case.name = meta["case_name"] or ext
            case.citation = cites.get(cluster_id)
            case.term = term_from_date(meta["date_filed"])
            case.decided = meta["date_filed"] or None
            case.extra = {"scdb_id": meta["scdb_id"], "cl_cluster_id": cluster_id}
            db.flush()
            case_id_by_cluster[cluster_id] = case.id
            # Clear any prior segments for idempotency.
            db.query(OpinionSegment).filter(OpinionSegment.case_id == case.id).delete()
            n_cases += 1
        db.commit()
        print(f"Created/updated {n_cases} cases. Streaming opinions ...")

        for cluster_id, kind, author, text in iter_segment_rows(args.opinions, cluster_ids):
            db.add(OpinionSegment(
                case_id=case_id_by_cluster[cluster_id],
                kind=kind, author_name=author, text=text,
            ))
            n_segments += 1
            if n_segments % 500 == 0:
                db.commit()
                print(f"  {n_segments} segments ...")
        db.commit()
    finally:
        db.close()

    print(f"Done: {n_cases} cases, {n_segments} segments.")
    print("Next: python -m scripts.build_justice_embeddings")


if __name__ == "__main__":
    main()
