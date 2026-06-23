# Leviathan SCOTUS (`scotusapp`)

**A reproducible research platform for analyzing Supreme Court opinions with NLP — segmentation,
lexical divergence, topic modeling, and per-justice style embeddings.**

> ⚠️ Same guardrails as the rest of Leviathan. "Ideological" analyses here are **lexical/stylistic
> statistics**, not measures of a justice's beliefs, motives, or correctness. Justice "groups" are
> unsupervised clusters of *writing style*, carry neutral labels, and should not be read as ideology
> scores — established external measures (e.g. Martin–Quinn) exist for that purpose. See
> [`../ETHICS.md`](../ETHICS.md).

## Features

| # | Feature | Module |
|---|---|---|
| 1 | Opinion corpus loader (CourtListener / local JSONL) | `corpus/loader.py` |
| 2 | Segmentation → majority / concurrence / dissent / per-curiam | `segmentation/segmenter.py` |
| 3 | Lexical divergence (majority vs dissent) + framing across justices | `analysis/lexical.py`, `analysis/framing.py` |
| 4 | Topic modeling (NMF) + curated constitutional-theme tagging | `analysis/topics.py` |
| 5 | Per-justice style embeddings | `analysis/justice_embeddings.py` |
| 6 | Similar-case finder across statistical divides | `similar.py` |
| 7 | Dashboard: justice similarity map, stylistic clustering, time evolution | `frontend/` |

## Why these methods

- **Lexical divergence** uses **Monroe, Colaresi & Quinn (2008) "Fightin' Words"** — weighted
  log-odds-ratio with an informative Dirichlet prior. It surfaces the words most distinctive of one
  side while down-weighting rare-word noise, which raw frequency or tf-idf do not. Pure NumPy, fully
  unit-tested.
- **Topic modeling** uses NMF over tf-idf (stable, interpretable) and maps components onto a curated
  constitutional-theme lexicon (first amendment, equal protection, federalism, economic regulation…).
- **Justice embeddings** mean-pool sentence-transformer vectors over each justice's authored
  segments, giving a *style* fingerprint; similarity/clustering operate on those.

## Run

Wired into the root `docker-compose.yml` (`scotus-api` :8002, `scotus-frontend` :3002, shares Postgres):

```bash
docker compose up --build scotus-api scotus-frontend
docker compose exec scotus-api python -m scripts.load_example_corpus
docker compose exec scotus-api python -m scripts.build_justice_embeddings
# API  http://localhost:8002/docs   ·   UI  http://localhost:3002
```

## API

| Endpoint | Purpose |
|---|---|
| `POST /corpus/ingest` | load + segment opinions |
| `GET /analysis/divergence?case_id=` | majority-vs-dissent distinctive words |
| `GET /analysis/topics` | NMF topics + theme distribution |
| `GET /justice/{id}` | a justice's profile, distinctive framing, neighbors |
| `GET /justice/similarity` | pairwise justice style-similarity matrix + clusters |
| `POST /similar-cases` | similar reasoning, flagged where it crosses statistical divides |
| `GET /analysis/evolution` | topic mix and style drift over terms |

## Validation against SCDB

`scotusapp/validation/scdb.py` + `scripts/validate_against_scdb.py` validate the label-producing
components against gold codings from the Supreme Court Database (issue area, winning party). Join is by
normalized U.S. citation; metrics are accuracy / macro-F1 / Cohen's κ. This is the empirical backbone
of the resource paper in [`../paper/`](../paper/README.md); see [`../paper/REPRODUCE.md`](../paper/REPRODUCE.md)
for the exact protocol. The bundled `example_scotus.jsonl` is synthetic and for smoke-testing only —
never for reported results.
