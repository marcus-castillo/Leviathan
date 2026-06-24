"""Compute SCDB validation metrics from a fetched JSONL sample, with NO database or torch.

Reads opinion records ({scdb_id, us_cite, case_name, text}) and the SCDB CSV, runs the theme tagger
and the rule-based outcome classifier on each majority text, joins to SCDB (by scdb_id, citation
fallback), and writes paper/results/scdb_validation.json. This is the offline twin of
validate_against_scdb.py for when the corpus is a JSONL rather than the Postgres store.

Usage:
    python -m scripts.validate_standalone --jsonl sample.jsonl --scdb SCDB.csv \
        --out ../paper/results/scdb_validation.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import scotusapp.config  # noqa: F401  (adds sibling backend/ to sys.path for the outcome classifier)
from scotusapp.analysis.topics import tag_themes
from scotusapp.validation.scdb import (
    SCDB_ISSUE_TO_THEME,
    align_labels,
    by_case_id,
    classification_metrics,
    load_scdb,
    normalize_cite,
    outcome_to_party_winning,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--scdb", required=True)
    ap.add_argument("--out", default="../paper/results/scdb_validation.json")
    args = ap.parse_args()

    from app.nlp.outcome import OutcomeClassifier

    clf = OutcomeClassifier()
    scdb = load_scdb(args.scdb)
    scdb_by_id = by_case_id(scdb)

    theme_pred: dict[str, object] = {}
    theme_gold: dict[str, object] = {}
    outcome_pred: dict[str, object] = {}
    outcome_gold: dict[str, object] = {}

    n_records = n_matched = 0
    for line in Path(args.jsonl).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        n_records += 1
        rec = json.loads(line)
        gold = scdb_by_id.get((rec.get("scdb_id") or "").strip())
        if gold is None:
            cite = normalize_cite(rec.get("us_cite"))
            gold = scdb.get(cite) if cite else None
        if gold is None:
            continue
        text = rec.get("text") or ""
        if not text.strip():
            continue
        key = gold.case_id or gold.us_cite
        n_matched += 1

        themes = tag_themes(text)
        theme_pred[key] = themes[0] if themes else None
        theme_gold[key] = SCDB_ISSUE_TO_THEME.get(gold.issue_area) if gold.issue_area else None

        outcome_pred[key] = outcome_to_party_winning(clf.predict(text).label)
        outcome_gold[key] = gold.party_winning if gold.party_winning in (0, 1) else None

    yt_t, yp_t, _ = align_labels(theme_gold, theme_pred)
    yt_o, yp_o, _ = align_labels(outcome_gold, outcome_pred)
    m_t = classification_metrics(yt_t, yp_t)
    m_o = classification_metrics(yt_o, yp_o)

    results = {
        "corpus": {"jsonl": str(args.jsonl), "records": n_records, "matched_to_scdb": n_matched,
                   "scdb_rows": len(scdb)},
        "issue_theme": {"n": m_t.n, "accuracy": m_t.accuracy, "macro_f1": m_t.macro_f1,
                        "cohen_kappa": m_t.cohen_kappa},
        "outcome_party_winning": {"n": m_o.n, "accuracy": m_o.accuracy, "macro_f1": m_o.macro_f1,
                                  "cohen_kappa": m_o.cohen_kappa},
        "note": ("Issue agreement scored over SCDB areas with a confident crosswalk; outcome over "
                 "cases SCDB codes as petitioner/respondent-winning. Rule-based outcome classifier."),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
