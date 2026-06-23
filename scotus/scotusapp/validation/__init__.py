"""Gold-label validation against the Supreme Court Database (SCDB).

Kept free of DB / heavy-model imports so the metric and crosswalk logic is unit-testable with only
stdlib + numpy + scikit-learn. The runtime glue (querying ingested opinions, applying classifiers)
lives in ``scripts/validate_against_scdb.py``.
"""
from scotusapp.validation.scdb import (
    SCDB_DECISION_DIRECTION,
    SCDB_ISSUE_AREA,
    SCDB_ISSUE_TO_THEME,
    SCDB_PARTY_WINNING,
    align_labels,
    by_case_id,
    classification_metrics,
    load_scdb,
    normalize_cite,
    outcome_to_party_winning,
)

__all__ = [
    "SCDB_DECISION_DIRECTION",
    "SCDB_ISSUE_AREA",
    "SCDB_ISSUE_TO_THEME",
    "SCDB_PARTY_WINNING",
    "align_labels",
    "by_case_id",
    "classification_metrics",
    "load_scdb",
    "normalize_cite",
    "outcome_to_party_winning",
]
