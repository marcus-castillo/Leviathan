"""Unit tests for the parts that don't need a DB or downloaded models."""
from __future__ import annotations

from app.bias.stats import benjamini_hochberg, two_proportion_ztest
from app.ethics.guardrails import build_caveats, enforce_no_intent_language
from app.nlp.issues import tag_issues
from app.nlp.outcome import OutcomeClassifier
from app.nlp.tone import analyze_tone
from app.config import settings


def test_no_intent_language_is_scrubbed():
    txt = "The judge is biased and acted with malice and intent to discriminate against the plaintiff."
    out = enforce_no_intent_language(txt)
    for banned in ("biased", "malice", "intent", "discriminate against"):
        assert banned not in out
    assert "statistical disparity" in out


def test_caveats_flag_small_samples():
    small = build_caveats(5)
    assert small.sample_warning is not None
    assert small.confidence < 0.4

    big = build_caveats(settings.min_sample_size * 4)
    assert big.sample_warning is None
    assert big.confidence >= small.confidence


def test_two_proportion_ztest_symmetry():
    t = two_proportion_ztest(8, 10, 2, 10)
    assert t.diff == round(0.8 - 0.2, 4)
    assert 0 <= t.p_value <= 1


def test_benjamini_hochberg_monotone():
    q = benjamini_hochberg([0.001, 0.04, 0.5])
    assert len(q) == 3
    assert all(0 <= x <= 1 for x in q)


def test_outcome_rule_based_detects_disposition():
    clf = OutcomeClassifier()
    pred = clf.predict("The motion to dismiss is granted. We affirm. The complaint is dismissed.")
    assert pred.label == "defendant"
    assert pred.confidence > 0.5


def test_tone_and_issue_tagging():
    text = "Plaintiff's section 1983 equal protection claim is persuasive and well-pleaded."
    assert "civil-rights" in tag_issues(text)
    tone = analyze_tone(text, parties=["Plaintiff"])
    assert tone.overall > 0
