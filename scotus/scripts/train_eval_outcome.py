"""Train + evaluate a SCOTUS outcome classifier on SCDB gold labels (offline; sklearn only).

Replaces the weak rule-based heuristic with a TF-IDF + logistic-regression model trained on SCDB
``partyWinning`` (petitioner vs respondent), evaluated on a held-out split. Also evaluates the
rule-based baseline on the same test set for a fair, honest comparison (coverage + accuracy), and the
keyword theme tagger against SCDB ``issueArea`` (no training needed). Writes the paper's results JSON.

No torch, no database. Inputs: the fetched JSONL ({scdb_id, text, ...}) and the SCDB CSV.

Usage:
    python -m scripts.train_eval_outcome --jsonl sample.jsonl --scdb SCDB.csv \
        --out ../paper/results/scdb_validation.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import scotusapp.config  # noqa: F401  (puts sibling backend/ on sys.path for the rule-based baseline)
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

SEED = 42


def _load_records(jsonl: str) -> list[dict]:
    return [json.loads(l) for l in Path(jsonl).read_text(encoding="utf-8").splitlines() if l.strip()]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--scdb", required=True)
    ap.add_argument("--out", default="../paper/results/scdb_validation.json")
    ap.add_argument("--test-size", type=float, default=0.3)
    args = ap.parse_args()

    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.model_selection import train_test_split

    scdb = load_scdb(args.scdb)
    scdb_by_id = by_case_id(scdb)
    records = _load_records(args.jsonl)

    # Resolve each record to its SCDB gold record.
    rows = []
    for rec in records:
        gold = scdb_by_id.get((rec.get("scdb_id") or "").strip())
        if gold is None:
            cite = normalize_cite(rec.get("us_cite"))
            gold = scdb.get(cite) if cite else None
        text = (rec.get("text") or "").strip()
        if gold is not None and text:
            rows.append((text, gold))

    n_matched = len(rows)

    # ----- Outcome: trained TF-IDF + logistic regression on partyWinning (0/1) -----
    xy = [(t, g.party_winning) for t, g in rows if g.party_winning in (0, 1)]
    outcome_trained = {"n_total": len(xy)}
    outcome_baseline = {}
    if len(xy) >= 40 and len({y for _, y in xy}) == 2:
        X = [t for t, _ in xy]
        y = [int(v) for _, v in xy]
        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=args.test_size, random_state=SEED, stratify=y)
        pipe_vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                                   max_features=20000, sublinear_tf=True, min_df=2)
        Xtr = pipe_vec.fit_transform(X_tr)
        clf = LogisticRegression(max_iter=2000, class_weight="balanced", random_state=SEED)
        clf.fit(Xtr, y_tr)
        pred = clf.predict(pipe_vec.transform(X_te)).tolist()
        m = classification_metrics(y_te, pred)
        outcome_trained.update({"n_train": len(y_tr), "n_test": m.n, "accuracy": m.accuracy,
                                "macro_f1": m.macro_f1, "cohen_kappa": m.cohen_kappa,
                                "model": "tfidf(1,2)+logreg", "test_size": args.test_size})

        # ----- Rule-based baseline on the SAME test cases (coverage + accuracy where it fires) -----
        from app.nlp.outcome import OutcomeClassifier

        rb = OutcomeClassifier()
        cov_true, cov_pred = [], []
        for t, yt in zip(X_te, y_te):
            p = outcome_to_party_winning(rb.predict(t).label)
            if p is not None:
                cov_true.append(yt)
                cov_pred.append(p)
        bm = classification_metrics(cov_true, cov_pred) if cov_true else None
        outcome_baseline = {
            "n_test": len(y_te),
            "coverage": round(len(cov_true) / len(y_te), 4) if y_te else 0.0,
            "n_covered": len(cov_true),
            "accuracy_on_covered": bm.accuracy if bm else None,
        }
    else:
        outcome_trained["note"] = f"insufficient labeled cases to train (n={len(xy)}); fetch more."

    # ----- Issue/theme: keyword tagger vs SCDB issueArea crosswalk (no training) -----
    theme_pred, theme_gold = {}, {}
    for i, (text, g) in enumerate(rows):
        theme_pred[i] = (tag_themes(text) or [None])[0]
        theme_gold[i] = SCDB_ISSUE_TO_THEME.get(g.issue_area) if g.issue_area else None
    yt, yp, _ = align_labels(theme_gold, theme_pred)
    mt = classification_metrics(yt, yp)

    results = {
        "corpus": {"jsonl": str(args.jsonl), "records": len(records),
                   "matched_to_scdb": n_matched, "scdb_rows": len(scdb)},
        "outcome_trained": outcome_trained,
        "outcome_rulebased_baseline": outcome_baseline,
        "issue_theme_tagger": {"n": mt.n, "accuracy": mt.accuracy, "macro_f1": mt.macro_f1,
                               "cohen_kappa": mt.cohen_kappa},
        "note": ("Outcome: TF-IDF+logreg trained on SCDB partyWinning, held-out test; baseline is the "
                 "rule-based classifier on the same test cases. Issue/theme: keyword tagger vs SCDB "
                 "issueArea over crosswalk-mapped areas. Stratified split, seed=42."),
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
