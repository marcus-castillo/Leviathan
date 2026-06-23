"""Supreme Court Database (SCDB) loader, label crosswalks, and validation metrics.

SCDB (Spaeth et al., http://scdb.wustl.edu) provides authoritative, human-coded labels for every
decision since 1946. We use the modern *case-centered* release (one row per case). Relevant columns:

    usCite             reporter citation, e.g. "347 U.S. 483"
    caseName
    term               OT term (year)
    partyWinning       0 = respondent won, 1 = petitioner won, 2 = unclear
    decisionDirection  1 = conservative, 2 = liberal, 3 = unspecifiable
    issueArea          1..14 (see SCDB_ISSUE_AREA)
    majOpinWriter      SCDB justice code of the majority author (needs the codebook to map to a name)

This module is deliberately dependency-light: the CSV loader uses stdlib ``csv``; metrics import
scikit-learn lazily. None of it touches the database, so it is unit-testable in isolation.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------- #
# SCDB code books (subset we use)
# --------------------------------------------------------------------------- #
SCDB_PARTY_WINNING = {0: "respondent", 1: "petitioner", 2: "unclear"}
SCDB_DECISION_DIRECTION = {1: "conservative", 2: "liberal", 3: "unspecifiable"}
SCDB_ISSUE_AREA = {
    1: "Criminal Procedure", 2: "Civil Rights", 3: "First Amendment", 4: "Due Process",
    5: "Privacy", 6: "Attorneys", 7: "Unions", 8: "Economic Activity", 9: "Judicial Power",
    10: "Federalism", 11: "Interstate Relations", 12: "Federal Taxation", 13: "Miscellaneous",
    14: "Private Action",
}

# Hand-constructed crosswalk from SCDB issueArea -> Leviathan theme lexicon keys.
# Only confident correspondences are mapped; the rest are excluded from agreement scoring (None).
# This crosswalk is a documented modeling decision (see paper, Validation section), not ground truth.
SCDB_ISSUE_TO_THEME: dict[int, str | None] = {
    1: "criminal-procedure",
    2: "civil-rights",
    3: "first-amendment",
    4: "due-process",
    5: "due-process",           # privacy is litigated largely through substantive due process
    6: None,
    7: "economic-regulation",   # labor/unions handled under economic regulation in our lexicon
    8: "economic-regulation",
    9: "separation-of-powers",  # judicial power ~ separation of powers
    10: "federalism",
    11: "federalism",
    12: "economic-regulation",  # federal taxation, coarse mapping
    13: None,
    14: None,
}


@dataclass
class SCDBRecord:
    case_id: str
    us_cite: str
    case_name: str
    term: int | None
    party_winning: int | None
    decision_direction: int | None
    issue_area: int | None
    maj_opin_writer: str | None


# --------------------------------------------------------------------------- #
# Loading / normalization
# --------------------------------------------------------------------------- #
def normalize_cite(cite: str | None) -> str:
    """Normalize a US reporter citation for joining, e.g. ' 347  u.s. 483 ' -> '347 U.S. 483'."""
    if not cite:
        return ""
    s = re.sub(r"\s+", " ", cite.strip()).upper()
    s = s.replace("U. S.", "U.S.").replace("US.", "U.S.").replace("U.S ", "U.S. ")
    return s


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return int(float(value))
    except ValueError:
        return None


def load_scdb(path: str | Path) -> dict[str, SCDBRecord]:
    """Load the case-centered SCDB CSV into a dict keyed by normalized US citation.

    Robust to the SCDB column set; missing optional columns are tolerated. Latin-1 is used because
    historical SCDB releases are not UTF-8.
    """
    records: dict[str, SCDBRecord] = {}
    with open(path, encoding="latin-1", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cite = normalize_cite(row.get("usCite"))
            if not cite:
                continue
            records[cite] = SCDBRecord(
                case_id=row.get("caseId", ""),
                us_cite=cite,
                case_name=row.get("caseName", ""),
                term=_to_int(row.get("term")),
                party_winning=_to_int(row.get("partyWinning")),
                decision_direction=_to_int(row.get("decisionDirection")),
                issue_area=_to_int(row.get("issueArea")),
                maj_opin_writer=(row.get("majOpinWriter") or None),
            )
    return records


# --------------------------------------------------------------------------- #
# Crosswalks for predicted labels
# --------------------------------------------------------------------------- #
def outcome_to_party_winning(outcome: str) -> int | None:
    """Map a Leviathan outcome label to the SCDB partyWinning space.

    Convention: the petitioner/appellant is the moving party (~ our 'plaintiff'); the
    respondent/appellee ~ our 'defendant'. 'mixed'/'unknown' are returned as None (excluded).
    """
    return {"plaintiff": 1, "defendant": 0}.get(outcome)


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
@dataclass
class MetricResult:
    n: int
    accuracy: float
    macro_f1: float
    cohen_kappa: float


def classification_metrics(y_true: list, y_pred: list) -> MetricResult:
    """Accuracy, macro-F1, and Cohen's kappa over aligned label lists (must be equal length)."""
    if len(y_true) != len(y_pred):
        raise ValueError("y_true and y_pred must have equal length")
    if not y_true:
        return MetricResult(0, 0.0, 0.0, 0.0)

    from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score

    return MetricResult(
        n=len(y_true),
        accuracy=round(float(accuracy_score(y_true, y_pred)), 4),
        macro_f1=round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
        cohen_kappa=round(float(cohen_kappa_score(y_true, y_pred)), 4),
    )


def align_labels(
    predicted: dict[str, object],
    gold: dict[str, object],
) -> tuple[list, list, int]:
    """Inner-join two citation-keyed label dicts.

    Returns ``(y_true, y_pred, n_unmatched_predictions)``. Entries whose gold or predicted value is
    None are dropped (so callers can use None to mean 'no confident label / excluded').
    """
    y_true: list = []
    y_pred: list = []
    unmatched = 0
    for cite, pred in predicted.items():
        if cite not in gold:
            unmatched += 1
            continue
        g = gold[cite]
        if g is None or pred is None:
            continue
        y_true.append(g)
        y_pred.append(pred)
    return y_true, y_pred, unmatched
