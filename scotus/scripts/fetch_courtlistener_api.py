"""Fetch a real SCOTUS sample from the CourtListener REST API into JSONL (text + SCDB join key).

A lighter alternative to the multi-GB bulk download. Strategy (chosen after testing for reliability
and rate limits): DRIVE FROM SCDB and BATCH the citation lookups. CourtListener's citation-lookup
endpoint resolves many citations in a single request, so we send chunks of ~100 SCDB citations, build
a citation->cluster map, then fetch each matched cluster's majority opinion text. This turns hundreds
of rate-limited lookups into a few requests. (The search/date-filtered-cluster endpoints were either
slow or dominated by cert-denial orders absent from SCDB.)

Reuses the dependency-free helpers in ``courtlistener_bulk``. Auth: COURTLISTENER_API_TOKEN from the
environment or ../.env.local.

Usage:
    python -m scripts.fetch_courtlistener_api --scdb SCDB.csv --out sample.jsonl --target 400 \
        --min-term 2003 --max-term 2019
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from scotusapp.corpus.courtlistener_bulk import opinion_type_to_kind, pick_text
from scotusapp.validation.scdb import load_scdb

API = "https://www.courtlistener.com/api/rest/v4"


def _token() -> str:
    tok = os.environ.get("COURTLISTENER_API_TOKEN")
    if not tok:
        envf = Path(__file__).resolve().parents[2] / ".env.local"
        if envf.exists():
            m = re.search(r"COURTLISTENER_API_TOKEN=([0-9a-fA-F]+)", envf.read_text())
            tok = m.group(1) if m else None
    if not tok:
        raise SystemExit("No COURTLISTENER_API_TOKEN (env or .env.local).")
    return tok


def _norm(c: str) -> str:
    return re.sub(r"\s+", " ", (c or "").strip()).upper()


def _request(url: str, token: str, data: bytes | None = None) -> dict | list:
    """GET/POST with long backoff on 429 (the citation-lookup limit resets per minute)."""
    req = urllib.request.Request(url, data=data, headers={
        "Authorization": f"Token {token}", "User-Agent": "Leviathan/0.1 research"})
    for attempt in range(8):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503):
                wait = 65 if e.code == 429 else 5 * (attempt + 1)
                print(f"  [{e.code}] backing off {wait}s ...", flush=True)
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(2 + attempt)
    return {}


def _lookup_chunk(cites: list[str], token: str) -> dict[str, dict]:
    """Resolve one chunk of citations in a single request; {normalized_cite: first_cluster}."""
    out: dict[str, dict] = {}
    body = urllib.parse.urlencode({"text": "; ".join(cites)}).encode()
    res = _request(f"{API}/citation-lookup/", token, data=body)
    if isinstance(res, list):
        for r in res:
            cl = r.get("clusters") or []
            if r.get("status") == 200 and cl:
                out[_norm(r.get("citation", ""))] = cl[0]
    return out


def _majority_text(cluster: dict, token: str, pause: float) -> str | None:
    longest = ""
    for opurl in cluster.get("sub_opinions", []):
        op = _request(opurl, token)
        time.sleep(pause)
        if not isinstance(op, dict):
            continue
        text = pick_text(op)
        if not text.strip():
            continue
        if opinion_type_to_kind(op.get("type"), bool(op.get("per_curiam"))) == "majority":
            return text
        if len(text) > len(longest):
            longest = text
    return longest or None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scdb", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--target", type=int, default=400)
    ap.add_argument("--min-term", type=int, default=2003)
    ap.add_argument("--max-term", type=int, default=2019)
    ap.add_argument("--pause", type=float, default=0.2, help="s between opinion fetches")
    ap.add_argument("--budget", type=float, default=540, help="wall-clock seconds before stopping")
    ap.add_argument("--max-batches", type=int, default=3, help="citation-lookup batches this run")
    args = ap.parse_args()

    token = _token()
    deadline = time.time() + args.budget
    out = Path(args.out)

    # APPEND + dedup: resume across runs (the citation-lookup endpoint throttles to ~1 batch/min, so
    # we accumulate the sample over several bounded runs instead of one long, killable job).
    done: set[str] = set()
    if out.exists():
        for line in out.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done.add(json.loads(line)["scdb_id"])

    scdb = load_scdb(args.scdb)
    sample = [r for r in scdb.values()
              if r.term and args.min_term <= r.term <= args.max_term
              and (r.sct_cite or r.us_cite) and r.case_id not in done]
    sample.sort(key=lambda r: (r.term, r.us_cite))
    print(f"SCDB terms {args.min_term}-{args.max_term}: {len(sample)} undone "
          f"({len(done)} already in {out.name})", flush=True)

    written = 0
    with out.open("a", encoding="utf-8") as fh:
        for b in range(args.max_batches):
            if len(done) + written >= args.target or time.time() >= deadline:
                break
            block = sample[b * 100:(b + 1) * 100]
            if not block:
                break
            resolved = _lookup_chunk([(r.sct_cite or r.us_cite) for r in block], token)
            print(f"  batch {b + 1}: resolved {len(resolved)}/{len(block)} "
                  f"(total={len(done) + written}, {deadline - time.time():.0f}s left)", flush=True)
            for r in block:
                if len(done) + written >= args.target or time.time() >= deadline:
                    break
                cluster = resolved.get(_norm(r.sct_cite or r.us_cite))
                if not cluster:
                    continue
                text = _majority_text(cluster, token, args.pause)
                if not text or len(text) < 200:
                    continue
                fh.write(json.dumps({
                    "scdb_id": r.case_id, "us_cite": r.us_cite,
                    "case_name": r.case_name, "term": r.term, "text": text,
                }) + "\n")
                fh.flush()
                written += 1

    print(f"DONE wrote {written} new; total now {len(done) + written} -> {out}", flush=True)


if __name__ == "__main__":
    main()
