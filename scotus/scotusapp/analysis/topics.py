"""Topic modeling + curated constitutional-theme tagging.

Two complementary views:
  * ``topic_model`` — unsupervised NMF over tf-idf, returning interpretable topics (top terms) and a
    document-topic matrix. NMF is stable and gives additive, readable components.
  * ``tag_themes`` — a transparent keyword tagger over a curated constitutional-theme lexicon, so
    every theme assignment traces to matched terms.
"""
from __future__ import annotations

THEME_LEXICON: dict[str, list[str]] = {
    "first-amendment": ["free speech", "establishment clause", "free exercise", "freedom of speech",
                        "expression", "religion", "press"],
    "equal-protection": ["equal protection", "discrimination", "suspect class", "strict scrutiny",
                         "racial", "classification"],
    "due-process": ["due process", "liberty interest", "fundamental right", "substantive due process"],
    "criminal-procedure": ["fourth amendment", "search and seizure", "warrant", "miranda",
                          "self-incrimination", "double jeopardy", "sentencing"],
    "federalism": ["commerce clause", "tenth amendment", "state sovereignty", "preemption",
                  "spending clause", "anti-commandeering"],
    "economic-regulation": ["regulation", "antitrust", "takings", "contract clause", "property",
                          "rate", "tariff", "interstate commerce"],
    "civil-rights": ["civil rights", "section 1983", "voting rights", "title vii", "desegregation"],
    "separation-of-powers": ["executive power", "separation of powers", "appointments clause",
                            "nondelegation", "removal power"],
}


def tag_themes(text: str, max_themes: int = 4) -> list[str]:
    low = text.lower()
    scored = []
    for theme, terms in THEME_LEXICON.items():
        hits = sum(low.count(t) for t in terms)
        if hits:
            scored.append((hits, theme))
    scored.sort(reverse=True)
    return [t for _, t in scored[:max_themes]]


def topic_model(documents: list[str], n_topics: int = 8, n_top_terms: int = 10,
                seed: int = 42) -> dict:
    """Fit NMF topics over the documents. Returns topics (top terms) and the doc-topic matrix."""
    if len(documents) < 2:
        return {"topics": [], "doc_topics": [], "note": "need >= 2 documents"}

    from sklearn.decomposition import NMF
    from sklearn.feature_extraction.text import TfidfVectorizer

    k = min(n_topics, len(documents))
    vec = TfidfVectorizer(max_df=0.95, min_df=1, stop_words="english", ngram_range=(1, 2))
    tfidf = vec.fit_transform(documents)
    terms = vec.get_feature_names_out()

    nmf = NMF(n_components=k, random_state=seed, init="nndsvda", max_iter=400)
    W = nmf.fit_transform(tfidf)  # doc x topic
    H = nmf.components_           # topic x term

    topics = []
    for ti in range(k):
        top_idx = H[ti].argsort()[::-1][:n_top_terms]
        topics.append({"topic": ti, "terms": [terms[i] for i in top_idx]})

    doc_topics = [int(row.argmax()) for row in W]
    return {"topics": topics, "doc_topics": doc_topics, "n_topics": k}
