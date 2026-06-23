"""Legal-issue tagging.

A lightweight, transparent keyword/topic tagger over a curated legal-issue lexicon. This is
deliberately interpretable (auditable) rather than a black-box classifier — every tag traces to
matched terms. Swap in a fine-tuned classifier via ``OUTCOME_MODEL_PATH``-style config if desired.
"""
from __future__ import annotations

ISSUE_LEXICON: dict[str, list[str]] = {
    "civil-rights": ["section 1983", "§ 1983", "equal protection", "due process", "civil rights"],
    "immigration": ["asylum", "removal", "deportation", "ina", "immigration judge", "withholding"],
    "criminal-procedure": ["fourth amendment", "suppress", "miranda", "search and seizure", "warrant"],
    "employment": ["title vii", "discrimination", "retaliation", "wrongful termination", "eeoc"],
    "first-amendment": ["free speech", "establishment clause", "free exercise", "first amendment"],
    "habeas": ["habeas corpus", "2254", "2255", "ineffective assistance"],
    "contract": ["breach of contract", "consideration", "damages", "specific performance"],
    "ip": ["patent", "trademark", "copyright", "infringement"],
    "tax": ["internal revenue", "irs", "deduction", "tax court"],
    "bankruptcy": ["chapter 7", "chapter 11", "debtor", "discharge", "trustee"],
}


def tag_issues(text: str, max_issues: int = 5) -> list[str]:
    low = text.lower()
    scored: list[tuple[int, str]] = []
    for issue, terms in ISSUE_LEXICON.items():
        hits = sum(low.count(t) for t in terms)
        if hits:
            scored.append((hits, issue))
    scored.sort(reverse=True)
    return [issue for _, issue in scored[:max_issues]]
