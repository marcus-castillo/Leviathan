"""Unit tests for the SCDB validation logic (no DB / models needed)."""
from __future__ import annotations

from scotusapp.validation.scdb import (
    SCDB_ISSUE_TO_THEME,
    align_labels,
    classification_metrics,
    normalize_cite,
    outcome_to_party_winning,
)


def test_normalize_cite():
    assert normalize_cite("  347  u.s. 483 ") == "347 U.S. 483"
    assert normalize_cite("410 U. S. 113") == "410 U.S. 113"
    assert normalize_cite(None) == ""


def test_outcome_crosswalk():
    assert outcome_to_party_winning("plaintiff") == 1
    assert outcome_to_party_winning("defendant") == 0
    assert outcome_to_party_winning("mixed") is None
    assert outcome_to_party_winning("unknown") is None


def test_issue_crosswalk_is_conservative():
    # Confident mappings present; ambiguous SCDB areas deliberately excluded (None).
    assert SCDB_ISSUE_TO_THEME[1] == "criminal-procedure"
    assert SCDB_ISSUE_TO_THEME[3] == "first-amendment"
    assert SCDB_ISSUE_TO_THEME[10] == "federalism"
    assert SCDB_ISSUE_TO_THEME[13] is None  # Miscellaneous -> excluded


def test_align_labels_inner_join_and_none_handling():
    pred = {"A": "x", "B": "y", "C": "z", "D": None}
    gold = {"A": "x", "B": "q", "D": "w"}  # C absent (unmatched); D pred is None (dropped)
    y_true, y_pred, unmatched = align_labels(pred, gold)
    assert unmatched == 1  # C
    assert sorted(zip(y_true, y_pred)) == [("q", "y"), ("x", "x")]


def test_classification_metrics_perfect_and_imperfect():
    perfect = classification_metrics(["a", "b", "a"], ["a", "b", "a"])
    assert perfect.accuracy == 1.0 and perfect.cohen_kappa == 1.0 and perfect.n == 3

    mixed = classification_metrics(["a", "b", "a", "b"], ["a", "a", "a", "b"])
    assert 0.0 <= mixed.accuracy <= 1.0 and -1.0 <= mixed.cohen_kappa <= 1.0
    assert mixed.accuracy == 0.75
