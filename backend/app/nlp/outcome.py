"""Outcome classification (who prevailed).

Two backends:
  * A fine-tuned HuggingFace sequence classifier if ``OUTCOME_MODEL_PATH`` is set (see
    ``scripts/train_outcome_classifier.py``).
  * Otherwise a transparent rule-based fallback over disposition language, so the system is usable
    with zero training. The fallback returns calibrated-ish confidences in [0, 1].

Outcome labels: "plaintiff", "defendant", "mixed", "unknown". These are coarse reductions of complex
dispositions and are intentionally probabilistic.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import settings

LABELS = ["plaintiff", "defendant", "mixed", "unknown"]

# Disposition cue phrases. Each maps toward who the disposition favors *by default convention*:
# in most postures, granting the defendant's dispositive motion favors the defendant.
_PLAINTIFF_CUES = [
    "judgment for the plaintiff", "in favor of the plaintiff", "plaintiff prevails",
    "motion to dismiss is denied", "we reverse", "we vacate and remand",
    "petition for review is granted", "we grant the petition", "appellant prevails",
]
_DEFENDANT_CUES = [
    "judgment for the defendant", "in favor of the defendant", "defendant prevails",
    "motion to dismiss is granted", "motion for summary judgment is granted",
    "we affirm", "petition for review is denied", "we deny the petition",
    "the complaint is dismissed",
]
_MIXED_CUES = ["granted in part and denied in part", "affirmed in part", "reversed in part"]


def _compile(cues: list[str]) -> list[re.Pattern]:
    return [re.compile(re.escape(c), re.IGNORECASE) for c in cues]


_P, _D, _M = _compile(_PLAINTIFF_CUES), _compile(_DEFENDANT_CUES), _compile(_MIXED_CUES)


@dataclass
class OutcomePrediction:
    label: str
    confidence: float


def _rule_based(text: str) -> OutcomePrediction:
    tail = text[-4000:]  # dispositions live near the end.
    p = sum(bool(r.search(tail)) for r in _P)
    d = sum(bool(r.search(tail)) for r in _D)
    m = sum(bool(r.search(tail)) for r in _M)

    if m and abs(p - d) <= 1:
        return OutcomePrediction("mixed", 0.5 + 0.1 * m)
    total = p + d
    if total == 0:
        return OutcomePrediction("unknown", 0.2)
    if p > d:
        return OutcomePrediction("plaintiff", round(min(0.9, 0.55 + 0.12 * (p - d)), 3))
    if d > p:
        return OutcomePrediction("defendant", round(min(0.9, 0.55 + 0.12 * (d - p)), 3))
    return OutcomePrediction("mixed", 0.45)


class OutcomeClassifier:
    """Lazily loads a transformer head if configured; else uses the rule-based fallback."""

    def __init__(self) -> None:
        self._hf = None
        if settings.outcome_model_path:
            self._load_hf(settings.outcome_model_path)

    def _load_hf(self, path: str) -> None:
        try:
            from transformers import pipeline as hf_pipeline

            self._hf = hf_pipeline("text-classification", model=path, truncation=True)
        except Exception:  # pragma: no cover - optional dependency / model
            self._hf = None

    def predict(self, text: str) -> OutcomePrediction:
        if self._hf is not None:
            res = self._hf(text[:4000])[0]
            label = res["label"].lower()
            if label not in LABELS:
                label = "unknown"
            return OutcomePrediction(label, round(float(res["score"]), 3))
        return _rule_based(text)
