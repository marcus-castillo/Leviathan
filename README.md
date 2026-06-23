# Leviathan

**Research-grade NLP system for quantifying *potential* statistical disparities in judicial opinions.**

> ⚠️ **Read this first — interpretation guardrails.**
> Leviathan measures **statistical patterns** in text and outcomes. It does **not** and **cannot** measure
> judicial *intent*, *malice*, or *prejudice*. Any number it produces is a descriptive statistic over a
> finite, non-random sample of opinions. Disparities can arise from caseload composition, the underlying
> law, selection effects, sampling noise, or modeling error — not just from the judge. Every output is
> emitted with a confidence score, a sample-size warning, and a limitations disclaimer. Treat all results
> as hypotheses requiring expert legal review, never as conclusions about a person.

---

## What it does

| Capability | Module |
|---|---|
| Ingest CourtListener opinions + federal text decisions w/ metadata | `app/ingestion` |
| Extract entities, legal issues, outcome, ruling *tone* | `app/nlp` |
| Outcome / sentiment / topic / citation disparity metrics | `app/bias` |
| Sentence-embedding similar-case retrieval & outcome comparison | `app/embeddings` |
| Statistical explanation + confidence + caveats for every signal | `app/bias/explain.py` |
| Ethics guardrails enforced on every response | `app/ethics` |
| Dashboard (rankings, court comparison, similarity explorer, trends) | `frontend/` |

## Architecture

```
CourtListener / text ──► ingestion ──► PostgreSQL ──► NLP pipeline ──► bias engine ──► FastAPI ──► Next.js
                                            ▲                              │
                                  sentence-transformers (pgvector) ◄───────┘
```

## Sub-projects

| Dir | What |
|---|---|
| `backend/` | FastAPI service: ingestion, NLP pipeline, bias engine, embeddings, ethics guardrails |
| `frontend/` | Next.js disparity dashboard |
| `corpus/` | **`levcorpus`** — offline ETL that turns raw opinions into a standardized, versioned dataset (JSONL/CSV/Parquet) for legal-NLP research. Reuses the backend NLP/embedding code; see [corpus/README.md](corpus/README.md). |
| `graph/` | **`graphapp`** — Neo4j citation graph + influence/cluster/temporal analysis (FastAPI) with a Cytoscape.js network explorer. Analytics run on NetworkX so they're testable without a live DB; see [graph/README.md](graph/README.md). |
| `scotus/` | **`scotusapp`** — Supreme Court opinion NLP: segmentation (majority/concurrence/dissent), majority-vs-dissent lexical divergence (Fightin' Words), topic modeling, and per-justice style embeddings, with a dashboard. See [scotus/README.md](scotus/README.md). |
| `landing/` | Unified landing page (nginx) linking both dashboards + all API docs. |
| `paper/` | Software/resource manuscript (LaTeX) validated against the Supreme Court Database; see [paper/README.md](paper/README.md) and [paper/REPRODUCE.md](paper/REPRODUCE.md). Result numbers are placeholders filled only from real pipeline runs. |

The `corpus` tool is a CLI, run on demand via the `tools` Docker profile:

```bash
docker compose --profile tools run --rm corpus ingest --source public-domain --path data/sample_opinions
docker compose --profile tools run --rm corpus preprocess
docker compose --profile tools run --rm corpus embed
docker compose --profile tools run --rm corpus export --bump minor --note "first slice"
```

The graph layer runs as its own services (`neo4j` on 7474/7687, `graph-api` on 8001, `graph-frontend`
on 3001):

```bash
docker compose up --build neo4j graph-api graph-frontend
docker compose exec graph-api python -m scripts.load_example_graph
docker compose exec graph-api python -m scripts.compute_metrics
```

The SCOTUS platform (`scotus-api` :8002, `scotus-frontend` :3002) and the unified landing page
(:8080) likewise:

```bash
docker compose up --build scotus-api scotus-frontend landing
docker compose exec scotus-api python -m scripts.load_example_corpus
docker compose exec scotus-api python -m scripts.build_justice_embeddings
# landing page: http://localhost:8080
```

## Quick start (Docker)

```bash
cp .env.example .env
docker compose up --build
# backend:  http://localhost:8000/docs
# frontend: http://localhost:3000
```

Then load the bundled example dataset and build the NLP + embedding artifacts:

```bash
docker compose exec backend python -m scripts.load_example_dataset
docker compose exec backend python -m scripts.build_embeddings
```

## Local dev (no Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm
uvicorn app.main:app --reload

cd ../frontend
npm install && npm run dev
```

## API

| Endpoint | Purpose |
|---|---|
| `POST /analyze-case` | Run the full NLP pipeline on a single opinion |
| `GET /judge-profile/{judge_id}` | Aggregated disparity metrics for one judge + caveats |
| `POST /compare-judges` | Side-by-side disparity comparison across judges |
| `POST /similar-cases` | Embedding retrieval + cross-judge outcome comparison |

Full schema at `/docs` (OpenAPI).

## Ethics & limitations

See [`ETHICS.md`](ETHICS.md). Short version: this is a tool for *research and oversight hypothesis
generation*. It deliberately uses the term **"tone analysis"** rather than "sentiment toward a party,"
avoids any language of intent, and refuses to rank judges without attaching dataset-size and
confidence warnings.
