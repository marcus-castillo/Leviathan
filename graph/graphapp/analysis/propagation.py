"""'Bias propagation' analysis — STRICTLY statistical grouping of judges by citation/topic profile.

Hard ethical line: this groups judges by *what areas of law they write in and how their citations
cluster*. It assigns neutral labels (Group 1, Group 2, ...). It does NOT infer ideology, political
lean, or bias, and the output explicitly says so. Groupings are artifacts of the corpus, the feature
set, and the chosen ``n_groups`` — change any of these and the groups change.
"""
from __future__ import annotations

import numpy as np

DISCLAIMER = (
    "Groups are unsupervised statistical clusters of citation/topic patterns ONLY. They are NOT "
    "ideological, political, or bias labels, carry no ordering, and are unstable under changes to the "
    "corpus, feature set, or number of groups. Do not interpret group membership as a claim about any "
    "judge's views or fairness."
)


def _vectorize(profiles: dict[str, dict]) -> tuple[list[str], list[str], np.ndarray]:
    """Build a judge × topic count matrix from ``{judge_id: {_name, topic: n, ...}}``."""
    topics = sorted({t for p in profiles.values() for t in p if not t.startswith("_")})
    judge_ids = list(profiles.keys())
    mat = np.zeros((len(judge_ids), len(topics)), dtype=float)
    for i, jid in enumerate(judge_ids):
        for j, t in enumerate(topics):
            mat[i, j] = profiles[jid].get(t, 0)
    # Row-normalize to topic *shares* so prolific judges don't dominate by volume.
    sums = mat.sum(axis=1, keepdims=True)
    sums[sums == 0] = 1.0
    return judge_ids, topics, mat / sums


def statistical_grouping(
    profiles: dict[str, dict],
    *,
    n_groups: int = 2,
    min_cases: int = 3,
    seed: int = 42,
) -> dict:
    """Cluster judges by normalized topic profile. Returns groups, members, and mandatory caveats."""
    # Filter judges with too little data to place.
    eligible = {
        jid: p for jid, p in profiles.items()
        if sum(v for k, v in p.items() if not k.startswith("_")) >= min_cases
    }
    if len(eligible) < n_groups:
        return {
            "groups": [],
            "n_judges": len(eligible),
            "note": f"Not enough judges with >= {min_cases} cases to form {n_groups} groups.",
            "disclaimer": DISCLAIMER,
        }

    from sklearn.cluster import KMeans

    judge_ids, topics, x = _vectorize(eligible)
    k = min(n_groups, len(judge_ids))
    km = KMeans(n_clusters=k, random_state=seed, n_init=10).fit(x)

    groups: list[dict] = []
    for g in range(k):
        idx = [i for i, lab in enumerate(km.labels_) if lab == g]
        centroid = km.cluster_centers_[g]
        top_topics = [topics[j] for j in np.argsort(centroid)[::-1][:3] if centroid[j] > 0]
        groups.append({
            "group": f"Group {g + 1}",
            "size": len(idx),
            "defining_topics": top_topics,
            "members": [
                {"judge_id": judge_ids[i], "name": eligible[judge_ids[i]].get("_name")}
                for i in idx
            ],
        })

    return {
        "groups": groups,
        "n_judges": len(judge_ids),
        "feature_space": "normalized topic shares of authored opinions",
        "n_groups": k,
        "disclaimer": DISCLAIMER,
    }
