"""Tests for segmentation, lexical divergence, topic/theme tagging, and justice-vector math.

None require a database, the backend encoder, or sentence-transformers.
"""
from __future__ import annotations

from scotusapp.analysis.justice_embeddings import mean_pool, nearest_justices, similarity_matrix
from scotusapp.analysis.lexical import cosine, tokenize, weighted_log_odds
from scotusapp.analysis.topics import tag_themes, topic_model
from scotusapp.segmentation import segment_opinion

SAMPLE = (
    "Syllabus. Irrelevant preamble.\n\n"
    "JUSTICE BRENNAN delivered the opinion of the Court. Freedom of speech is protected. "
    "We reverse.\n\n"
    "CHIEF JUSTICE ROBERTS, concurring. I agree with the judgment only.\n\n"
    "JUSTICE SCALIA, with whom JUSTICE THOMAS joins, dissenting. The text controls. I dissent."
)


# --------------------------------------------------------------------------- #
# Segmentation
# --------------------------------------------------------------------------- #
def test_segments_majority_concurrence_dissent():
    segs = segment_opinion(SAMPLE)
    kinds = {s.kind for s in segs}
    assert "majority" in kinds and "concurrence" in kinds and "dissent" in kinds
    maj = next(s for s in segs if s.kind == "majority")
    assert maj.author == "BRENNAN"
    dis = next(s for s in segs if s.kind == "dissent")
    assert dis.author == "SCALIA"
    assert "Irrelevant preamble" not in maj.text  # preamble dropped


def test_per_curiam_and_no_header_fallback():
    assert segment_opinion("PER CURIAM. The petition is denied.")[0].kind == "per_curiam"
    fallback = segment_opinion("An opinion with no headers at all.")
    assert len(fallback) == 1 and fallback[0].kind == "majority"


# --------------------------------------------------------------------------- #
# Lexical divergence (Fightin' Words)
# --------------------------------------------------------------------------- #
def test_weighted_log_odds_separates_vocabularies():
    a = ["liberty expression speech expression liberty speech robust"] * 5
    b = ["sovereignty federalism commerce sovereignty commerce tenth"] * 5
    res = weighted_log_odds(a, b, top_k=5, min_count=2)
    a_words = {w for w, _ in res["a"]}
    b_words = {w for w, _ in res["b"]}
    assert "expression" in a_words or "speech" in a_words
    assert "sovereignty" in b_words or "commerce" in b_words
    # distinctive-of-A words score positive, distinctive-of-B negative
    assert all(z > 0 for _, z in res["a"]) and all(z < 0 for _, z in res["b"])


def test_tokenize_drops_stopwords():
    toks = tokenize("The Court held that the statute was valid.")
    assert "the" not in toks and "court" not in toks and "statute" in toks


# --------------------------------------------------------------------------- #
# Topics / themes
# --------------------------------------------------------------------------- #
def test_theme_tagging():
    assert "first-amendment" in tag_themes("This concerns freedom of speech and free exercise.")
    assert "federalism" in tag_themes("The commerce clause and tenth amendment limit federal power.")


def test_topic_model_runs():
    docs = [
        "speech expression first amendment freedom",
        "commerce federalism sovereignty tenth amendment",
        "search seizure fourth amendment warrant probable cause",
        "equal protection discrimination strict scrutiny classification",
    ]
    model = topic_model(docs, n_topics=2)
    assert model["n_topics"] == 2 and len(model["topics"]) == 2


# --------------------------------------------------------------------------- #
# Justice vector math
# --------------------------------------------------------------------------- #
def test_mean_pool_and_similarity():
    vecs = {"a": mean_pool([[1.0, 0.0], [1.0, 0.0]]), "b": [0.0, 1.0], "c": [0.9, 0.1]}
    assert cosine(vecs["a"], vecs["c"]) > cosine(vecs["a"], vecs["b"])
    sim = similarity_matrix(vecs)
    assert sim["justices"] == ["a", "b", "c"]
    near = nearest_justices(vecs, "a", k=1)
    assert near and near[0]["justice"] == "c"
