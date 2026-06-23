# Leviathan — Ethics, Scope, and Limitations

Leviathan is designed for **defensive, oversight-oriented research**: helping scholars, journalists, and
court-accountability researchers *generate hypotheses* about statistical disparities that merit expert
human review. It is **not** a verdict machine and must never be presented as one.

## Hard rules enforced in code (`app/ethics/guardrails.py`)

1. **No intent claims.** Output language is restricted to statistical/descriptive vocabulary
   ("disparity", "association", "difference in rates"). Words implying mental state, malice, or
   prejudice are blocked from generated narratives.
2. **Statistical framing only.** Every metric ships with: effect size, a confidence score, the n it was
   computed over, and an explicit limitations string.
3. **Dataset-size gating.** Below a configurable minimum sample (`MIN_SAMPLE_SIZE`, default 30), the
   system refuses point estimates and returns a "insufficient data" signal instead of a ranking.
4. **Tone, not sentiment-about-a-person.** Language analysis is framed as *tone of ruling language*, a
   property of the text, not a measure of feeling toward a litigant.
5. **Confounds surfaced, not hidden.** Explanations name the most common confounds (caseload mix, area
   of law, appellate posture, sampling noise) so a reader cannot mistake correlation for cause.

## Known limitations

- **Sampling bias:** CourtListener coverage is uneven across courts and eras. Absence of data is not
  data.
- **Outcome labeling is noisy:** "win/loss" is a coarse reduction of complex dispositions
  (partial grants, remands, mootness). The classifier is probabilistic.
- **Tone ≠ fairness:** terse or harsh language may reflect the law or the record, not bias.
- **Multiple comparisons:** comparing many judges inflates false positives; p-values are
  Benjamini–Hochberg adjusted but small-n caveats still dominate.
- **No causal identification:** nothing here is a controlled experiment.

## Responsible use

Do not publish per-judge claims of bias from Leviathan output alone. Use it to decide *where to look*,
then have qualified people read the actual opinions.
