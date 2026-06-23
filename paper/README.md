# Paper: Leviathan resource/software article

A manuscript scaffold for a **software/resource paper** validated against the Supreme Court Database.

## Files
- `main.tex` — manuscript. Result-dependent numbers are marked `[FILL: ...]` (rendered in red).
- `references.bib` — bibliography (verify entries before submission).
- `REPRODUCE.md` — maps every `[FILL]` to the command that generates it.
- `results/` — generated JSON from validation runs (git-ignored except `.gitkeep`).
- `Makefile` — `make` builds `main.pdf` (needs a TeX distribution).

## Status
Prose that does not depend on results (architecture, methods, related work, ethics, reproducibility)
is written. **All empirical numbers are placeholders** until you run the pipeline on a real corpus +
SCDB and fill them via `REPRODUCE.md`. Do not submit with any `[FILL]` marker remaining.

## Target venues (software/resource)
- **SoftwareX** (Elsevier) — software metapaper; fits the "describe + validate + impact" structure here.
- **Journal of Open Source Software (JOSS)** — note: JOSS papers are very short and do *not* include a
  validation/results section; the validation here would live in the repo/docs, and `main.tex` would be
  trimmed to a Summary + Statement of Need. JOSS also requires substantial documentation and tests
  (already present).
- An **arXiv preprint** first is advisable regardless.

## Authorship & integrity
- Set the author list/affiliations before submission.
- Disclose tooling/AI assistance per the target venue's policy.
- The repository's CI, tests, and dataset versioning are part of the artifact — link the exact commit.
