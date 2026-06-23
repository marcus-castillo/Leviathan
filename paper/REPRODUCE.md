# Reproducing every number in the paper

This manuscript reports **no hand-entered results**. Each `[FILL: ...]` marker in `main.tex` is
filled from an artifact produced by a command below. If a number isn't produced by one of these,
it does not go in the paper.

## 0. Environment

Record the exact environment in the paper's "Software environment" line:

```bash
git rev-parse HEAD                  # commit hash
docker compose images               # image digests
python -c "import sentence_transformers, sklearn; print(sentence_transformers.__version__, sklearn.__version__)"
```

## 1. Bring up the stack and ingest a real SCOTUS corpus

The bundled `example_scotus.jsonl` is **synthetic** and is for smoke-testing only — it must NOT be
used for reported results. Ingest real opinions (e.g. via the CourtListener SCOTUS endpoint or a
local bulk download), then build embeddings:

```bash
docker compose up --build db scotus-api
# ... load a real corpus into scotus_case / scotus_segment (CourtListener loader or your own) ...
docker compose exec scotus-api python -m scripts.build_justice_embeddings
```

Report the corpus size, term range, and source in Table 1's caption.

## 2. Download SCDB gold labels

Download the **case-centered, citation-organized** CSV from
<http://supremecourtdatabase.org/data.php> (e.g. `SCDB_2023_01_caseCentered_Citation.csv`).
Cite the exact release version in the paper.

## 3. Run validation -> Table 1

```bash
docker compose exec scotus-api \
  python -m scripts.validate_against_scdb --scdb /data/SCDB_2023_01_caseCentered_Citation.csv \
  --out ../paper/results/scdb_validation.json
```

This writes `paper/results/scdb_validation.json`. Copy its fields into the abstract and Table 1:

| Paper marker | JSON field |
|---|---|
| Issue/theme `N` / acc / F1 / κ | `issue_theme.{n,accuracy,macro_f1,cohen_kappa}` |
| Outcome `N` / acc / F1 / κ | `outcome_party_winning.{n,accuracy,macro_f1,cohen_kappa}` |

## 4. Illustrative example (Section 6)

Pick one real case id and capture pipeline outputs verbatim:

```bash
curl -s "http://localhost:8002/analysis/divergence?case_id=<ID>" | tee paper/results/example_divergence.json
curl -s "http://localhost:8002/justice/<slug>"                    | tee paper/results/example_justice.json
```

## 5. Segmentation statistics (Section 5)

Reported by the same validation script (intrinsic stats) and, if you supply the SCDB justice
codebook mapping `majOpinWriter` codes to surnames, the majority-author attribution accuracy.

## 6. Build the PDF

```bash
cd paper && make
```

> Integrity check before submission: grep the source for unfilled markers — there must be none.
>
> ```bash
> ! grep -n "FILL:" paper/main.tex
> ```
