"""Per-justice style embeddings + similarity / clustering.

A justice's *style fingerprint* is the mean of their authored-segment sentence-transformer vectors.
The pooling, similarity matrix, and clustering here are pure (operate on given vectors), so they're
testable without the encoder; the encoder is only invoked when building segment vectors.
"""
from __future__ import annotations

import numpy as np

from scotusapp.analysis.lexical import cosine


def mean_pool(vectors: list[list[float]]) -> list[float] | None:
    if not vectors:
        return None
    arr = np.asarray(vectors, dtype=float)
    v = arr.mean(axis=0)
    n = np.linalg.norm(v)
    return (v / n).tolist() if n else v.tolist()


def similarity_matrix(justice_vectors: dict[str, list[float]]) -> dict:
    """Pairwise cosine similarity between justice style vectors."""
    names = [j for j, v in justice_vectors.items() if v]
    matrix = [[round(cosine(justice_vectors[a], justice_vectors[b]), 4) for b in names] for a in names]
    return {"justices": names, "matrix": matrix}


def nearest_justices(justice_vectors: dict[str, list[float]], target: str, k: int = 5) -> list[dict]:
    if target not in justice_vectors or not justice_vectors[target]:
        return []
    sims = [
        {"justice": j, "similarity": round(cosine(justice_vectors[target], v), 4)}
        for j, v in justice_vectors.items()
        if j != target and v
    ]
    return sorted(sims, key=lambda d: d["similarity"], reverse=True)[:k]


def style_clusters(justice_vectors: dict[str, list[float]], n_clusters: int = 3,
                   seed: int = 42) -> dict:
    """Cluster justices by STYLE vector. Neutral labels — not ideology (see ethics)."""
    names = [j for j, v in justice_vectors.items() if v]
    if len(names) < 2:
        return {"clusters": [], "note": "need >= 2 justices with embeddings"}

    from sklearn.cluster import KMeans

    x = np.asarray([justice_vectors[j] for j in names], dtype=float)
    k = min(n_clusters, len(names))
    labels = KMeans(n_clusters=k, random_state=seed, n_init=10).fit_predict(x)

    clusters: dict[int, list[str]] = {}
    for name, lab in zip(names, labels):
        clusters.setdefault(int(lab), []).append(name)
    return {
        "clusters": [{"cluster": f"Cluster {c + 1}", "justices": members}
                     for c, members in sorted(clusters.items())],
        "n_clusters": k,
    }
