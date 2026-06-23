"""Validate Leviathan's SCOTUS predictions against SCDB gold labels and emit a results table.

Pipeline:
  1. Load the SCDB case-centered CSV (download from http://scdb.wustl.edu).
  2. For each ingested case, derive predictions from the majority segment:
       - issue/theme  : analysis.topics.tag_themes (top theme)  -> compared to SCDB issueArea
       - outcome      : backend OutcomeClassifier               -> compared to SCDB partyWinning
  3. Join on normalized US citation; compute accuracy / macro-F1 / Cohen's kappa.
  4. Write paper/results/scdb_validation.json (consumed by the manuscript's Validation section).

Usage:
    python -m scripts.validate_against_scdb --scdb /path/SCDB_2023_01_caseCentered_Citation.csv

Requires an ingested SCOTUS corpus (scripts.load_example_corpus, or a real CourtListener load) AND a
running Postgres. The numbers this prints are the ONLY source for the paper's validation tables --
do not hand-edit them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import select

from scotusapp.analysis.topics import tag_themes
from scotusapp.db import Case, OpinionSegment, SessionLocal, init_db
from scotusapp.validation.scdb import (
    SCDB_ISSUE_TO_THEME,
    align_labels,
    classification_metrics,
    load_scdb,
    normalize_cite,
    outcome_to_party_winning,
)


def _majority_text(case: Case) -> str | None:
    for seg in case.segments:
        if seg.kind == "majority":
            return seg.text
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scdb", required=True, help="SCDB case-centered CSV path")
    ap.add_argument("--out", default="../paper/results/scdb_validation.json")
    args = ap.parse_args()

    init_db()
    scdb = load_scdb(args.scdb)
    print(f"Loaded {len(scdb)} SCDB rows.")

    # Backend outcome classifier (rule-based fallback unless OUTCOME_MODEL_PATH is set).
    from app.nlp.outcome import OutcomeClassifier

    clf = OutcomeClassifier()

    theme_pred: dict[str, object] = {}
    theme_gold: dict[str, object] = {}
    outcome_pred: dict[str, object] = {}
    outcome_gold: dict[str, object] = {}

    db = SessionLocal()
    try:
        cases = db.execute(select(Case)).scalars().all()
        for case in cases:
            cite = normalize_cite(case.citation)
            if not cite or cite not in scdb:
                continue
            gold = scdb[cite]
            text = _majority_text(case)
            if not text:
                continue

            # Theme: top predicted theme vs SCDB issueArea crosswalk.
            themes = tag_themes(text)
            theme_pred[cite] = themes[0] if themes else None
            theme_gold[cite] = (
                SCDB_ISSUE_TO_THEME.get(gold.issue_area) if gold.issue_area else None
            )

            # Outcome: classifier vs SCDB partyWinning.
            outcome_pred[cite] = outcome_to_party_winning(clf.predict(text).label)
            outcome_gold[cite] = (
                gold.party_winning if gold.party_winning in (0, 1) else None
            )
    finally:
        db.close()

    yt_theme, yp_theme, unmatched_t = align_labels(theme_gold, theme_pred)
    yt_out, yp_out, unmatched_o = align_labels(outcome_gold, outcome_pred)
    m_theme = classification_metrics(yt_theme, yp_theme)
    m_out = classification_metrics(yt_out, yp_out)

    results = {
        "n_scdb_rows": len(scdb),
        "issue_theme": {
            "n": m_theme.n, "accuracy": m_theme.accuracy,
            "macro_f1": m_theme.macro_f1, "cohen_kappa": m_theme.cohen_kappa,
        },
        "outcome_party_winning": {
            "n": m_out.n, "accuracy": m_out.accuracy,
            "macro_f1": m_out.macro_f1, "cohen_kappa": m_out.cohen_kappa,
        },
        "note": (
            "Issue agreement is scored only over SCDB areas with a confident crosswalk; outcome over "
            "cases SCDB codes as petitioner/respondent-winning. See paper Validation section."
        ),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print(json.dumps(results, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
