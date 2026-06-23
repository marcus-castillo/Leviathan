"""Framing differences across justices.

For a given justice, compute the vocabulary most distinctive of their writing vs. all other justices
(weighted log-odds). This captures *framing* — the terms a justice reaches for — as a lexical
statistic, not a claim about views.
"""
from __future__ import annotations

from scotusapp.analysis.lexical import weighted_log_odds


def justice_framing(
    justice_texts: dict[str, list[str]],
    target: str,
    *,
    top_k: int = 20,
) -> dict:
    """Distinctive vocabulary of ``target`` justice vs. the rest of the corpus."""
    if target not in justice_texts:
        return {"target": target, "distinctive": [], "note": "no segments for this justice"}

    own = justice_texts[target]
    others = [t for j, texts in justice_texts.items() if j != target for t in texts]
    if not own or not others:
        return {"target": target, "distinctive": [], "note": "insufficient comparison corpus"}

    res = weighted_log_odds(own, others, top_k=top_k)
    return {
        "target": target,
        "distinctive": res["a"],          # words this justice over-uses relative to peers
        "underused": res["b"][:top_k],    # words they under-use relative to peers
    }
