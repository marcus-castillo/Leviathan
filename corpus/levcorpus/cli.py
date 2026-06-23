"""levcorpus command-line interface.

Commands:
    init-db                      create extension + tables
    ingest                       collect raw opinions (courtlistener | public-domain)
    preprocess                   structured extraction + auto annotation
    embed                        per-case sentence-transformer embeddings
    export                       standardized, versioned JSONL/CSV/Parquet release
    versions                     list dataset versions + reproducibility info
"""
from __future__ import annotations

import argparse
import json
import sys

from levcorpus.db import SessionLocal, init_db


def _cmd_init_db(args: argparse.Namespace) -> int:
    init_db()
    print("Initialized corpus tables (corpus_raw, corpus_record) + pgvector extension.")
    return 0


def _cmd_ingest(args: argparse.Namespace) -> int:
    from levcorpus.collect import collect_courtlistener, collect_public_domain

    db = SessionLocal()
    try:
        if args.source == "courtlistener":
            n = collect_courtlistener(db, court=args.court, query=args.query, limit=args.limit)
            print(f"Collected {n} new opinion(s) from CourtListener.")
        elif args.source == "public-domain":
            if not args.path:
                print("--path is required for --source public-domain", file=sys.stderr)
                return 2
            n = collect_public_domain(db, args.path)
            print(f"Collected {n} new opinion(s) from {args.path}.")
        else:
            print(f"Unknown source: {args.source}", file=sys.stderr)
            return 2
    finally:
        db.close()
    return 0


def _cmd_preprocess(args: argparse.Namespace) -> int:
    from levcorpus.pipeline import preprocess_pending

    db = SessionLocal()
    try:
        n = preprocess_pending(db, reprocess=args.reprocess, limit=args.limit)
        print(f"Standardized {n} record(s).")
    finally:
        db.close()
    return 0


def _cmd_embed(args: argparse.Namespace) -> int:
    from levcorpus.pipeline import embed_pending

    db = SessionLocal()
    try:
        n = embed_pending(db, reembed=args.reembed, limit=args.limit)
        print(f"Embedded {n} record(s).")
    finally:
        db.close()
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    from levcorpus.pipeline import export_dataset

    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    db = SessionLocal()
    try:
        manifest = export_dataset(
            db, formats=formats, bump=args.bump, version=args.version,
            note=args.note, include_embeddings=not args.no_embeddings,
        )
    finally:
        db.close()
    print(f"Released dataset v{manifest['version']} "
          f"({manifest['row_count']} rows, hash {manifest['content_hash'][:12]}).")
    for fmt, info in manifest["files"].items():
        print(f"  {fmt}: {info['file']} ({info['rows']} rows, {info['bytes']} bytes)")
    if manifest["schema_diff"]["added_fields"] or manifest["schema_diff"]["removed_fields"]:
        print(f"  schema diff: {manifest['schema_diff']}")
    return 0


def _cmd_versions(args: argparse.Namespace) -> int:
    from levcorpus.versioning import VersionRegistry

    versions = VersionRegistry().list_versions()
    if not versions:
        print("No dataset versions released yet.")
        return 0
    if args.json:
        print(json.dumps(versions, indent=2))
        return 0
    for v in versions:
        print(f"v{v['version']:8} rows={v['row_count']:<6} hash={v['content_hash'][:12]} "
              f"{v['created_at'][:19]}  {v.get('note','')}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="levcorpus", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="create tables + pgvector extension").set_defaults(func=_cmd_init_db)

    ing = sub.add_parser("ingest", help="collect raw opinions")
    ing.add_argument("--source", required=True, choices=["courtlistener", "public-domain"])
    ing.add_argument("--court", help="CourtListener court id, e.g. ca9")
    ing.add_argument("--query", help="CourtListener full-text query")
    ing.add_argument("--path", help="file/dir for public-domain ingestion")
    ing.add_argument("--limit", type=int, default=25)
    ing.set_defaults(func=_cmd_ingest)

    pre = sub.add_parser("preprocess", help="structured extraction + annotation")
    pre.add_argument("--reprocess", action="store_true", help="rebuild all records")
    pre.add_argument("--limit", type=int)
    pre.set_defaults(func=_cmd_preprocess)

    emb = sub.add_parser("embed", help="generate per-case embeddings")
    emb.add_argument("--reembed", action="store_true", help="recompute all embeddings")
    emb.add_argument("--limit", type=int)
    emb.set_defaults(func=_cmd_embed)

    exp = sub.add_parser("export", help="standardized versioned export")
    exp.add_argument("--formats", default="jsonl,csv,parquet")
    exp.add_argument("--bump", choices=["major", "minor", "patch"], default="minor")
    exp.add_argument("--version", help="explicit version, e.g. 1.0.0 (overrides --bump)")
    exp.add_argument("--note", default="")
    exp.add_argument("--no-embeddings", action="store_true", help="exclude embedding vectors")
    exp.set_defaults(func=_cmd_export)

    ver = sub.add_parser("versions", help="list dataset versions")
    ver.add_argument("--json", action="store_true")
    ver.set_defaults(func=_cmd_versions)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
