"""Lexical divergence between two sets of opinion text.

Implements the weighted log-odds-ratio with an informative Dirichlet prior from
Monroe, Colaresi & Quinn (2008), "Fightin' Words". For each word w, the statistic is the z-score of
the log-odds difference between corpus A and corpus B, with the background corpus (A+B) supplying the
prior. Large positive z => distinctive of A; large negative => distinctive of B. The prior shrinks
rare-word noise, which raw frequency / tf-idf do not. Pure NumPy — fully unit-testable.
"""
from __future__ import annotations

import math
import re
from collections import Counter

import numpy as np

_WORD_RE = re.compile(r"[a-z][a-z'\-]{2,}")

# Minimal legal/English stopword set (kept small + explicit for auditability).
_STOP = {
    "the", "and", "that", "for", "this", "with", "not", "are", "was", "but", "his", "her",
    "from", "which", "would", "could", "have", "has", "had", "its", "their", "any", "all",
    "such", "may", "shall", "under", "upon", "into", "than", "then", "thus", "where", "when",
    "also", "see", "id", "ante", "post", "supra", "ibid", "cf", "e.g", "i.e", "court", "courts",
    "case", "cases", "opinion", "justice", "u.s", "v", "j", "no",
}


def tokenize(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOP]


def _counts(texts: list[str]) -> Counter:
    c: Counter = Counter()
    for t in texts:
        c.update(tokenize(t))
    return c


def weighted_log_odds(
    texts_a: list[str],
    texts_b: list[str],
    *,
    top_k: int = 25,
    min_count: int = 2,
    alpha: float = 0.01,
) -> dict:
    """Return words most distinctive of A vs B.

    ``alpha`` scales the (uniform) Dirichlet prior derived from the combined corpus. Returns
    ``{"a": [(word, z), ...], "b": [...], "scores": {word: z}}`` where A-distinctive words have the
    most positive z and B-distinctive the most negative.
    """
    ca, cb = _counts(texts_a), _counts(texts_b)
    vocab = {w for w, n in (ca + cb).items() if (ca[w] + cb[w]) >= min_count}
    if not vocab:
        return {"a": [], "b": [], "scores": {}}

    na, nb = sum(ca[w] for w in vocab), sum(cb[w] for w in vocab)
    # Informative prior: total count of w across both corpora, scaled by alpha.
    a0 = {w: alpha * (ca[w] + cb[w]) for w in vocab}
    sum_a0 = sum(a0.values())

    scores: dict[str, float] = {}
    for w in vocab:
        yi_a, yi_b = ca[w], cb[w]
        # log-odds with prior
        log_odds = (
            math.log((yi_a + a0[w]) / (na + sum_a0 - yi_a - a0[w]))
            - math.log((yi_b + a0[w]) / (nb + sum_a0 - yi_b - a0[w]))
        )
        # variance of the log-odds estimate
        var = 1.0 / (yi_a + a0[w]) + 1.0 / (yi_b + a0[w])
        scores[w] = log_odds / math.sqrt(var)

    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top_a = [(w, round(z, 3)) for w, z in ordered[:top_k] if z > 0]
    top_b = [(w, round(z, 3)) for w, z in ordered[::-1][:top_k] if z < 0]
    return {"a": top_a, "b": top_b, "scores": {w: round(z, 4) for w, z in scores.items()}}


def cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(va @ vb / (na * nb))
