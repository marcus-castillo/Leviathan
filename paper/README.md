# Paper: Leviathan resource/software article

A manuscript scaffold for a **software/resource paper** validated against the Supreme Court Database.

## Files
- `main.tex` — manuscript. Result-dependent numbers are marked `[FILL: ...]` (rendered in red).
- `references.bib` — bibliography (verify entries before submission).
- `REPRODUCE.md` — maps every `[FILL]` to the command that generates it.
- `results/` — generated JSON from validation runs (git-ignored except `.gitkeep`).
- `Makefile` — `make` builds `main.pdf` (needs a TeX distribution).

## Status
`main.tex` is formatted for **SoftwareX** (Elsevier `elsarticle` class, the required *Code metadata*
table, and the SoftwareX section order: Motivation and significance → Software description →
Illustrative examples → Impact → Conclusions). Prose that does not depend on results is written.
**All empirical numbers are placeholders** (`[FILL]`, red) until you run the pipeline on a real corpus
+ SCDB and fill them via `REPRODUCE.md`. Do not submit with any `[FILL]` marker remaining.

## Build requirements
Needs the `elsarticle` class (ships with TeX Live's `texlive-publishers`) and `elsarticle-num.bst`.
`make` runs pdflatex → bibtex → pdflatex×2.

## SoftwareX submission checklist
- [ ] Set author affiliation (frontmatter `\address`) and Acknowledgements (incl. AI-assistance disclosure).
- [ ] Archive a tagged release to **Zenodo** and put the DOI in Code-metadata C2.
- [ ] (Recommended) Create a **Code Ocean** reproducible capsule for C3.
- [ ] License: repository ships **MIT** (`/LICENSE`); matches metadata C4. Swap to Apache-2.0 if you want explicit patent terms.
- [ ] Fill every `[FILL]` from a real run; verify with `! grep -n "FILL:" paper/main.tex`.
- [ ] Consider an **arXiv** preprint first.

## Authorship & integrity
- The repository's CI, tests, and dataset versioning are part of the artifact — link the exact commit / Zenodo DOI.
- Disclose AI-assisted development per SoftwareX policy.
