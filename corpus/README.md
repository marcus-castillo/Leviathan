# Leviathan Corpus (`levcorpus`)

**A reproducible pipeline that turns raw judicial opinions into a standardized, versioned dataset for
legal-NLP and judicial-disparity research.**

> ⚠️ Same guardrails as the parent project apply. Annotations here (especially `sentiment_proxy` and
> `decision_direction`) are **weak, automatically generated proxies**, not ground truth and not
> measures of intent. See [`../ETHICS.md`](../ETHICS.md). `decision_direction` is a *structural* label
> (who prevailed), **not** an ideological/political coding.

## Why it's separate from the backend

The `backend/` service answers live API queries. `corpus/` is an **offline ETL tool** whose output is
a *file artifact* (JSONL / CSV / Parquet) you can hand to other researchers, load into a notebook, or
check into DVC. To avoid drift, it **reuses** the backend's NLP pipeline, CourtListener client, and
embedding encoder rather than reimplementing them; it adds structured extraction, the canonical
schema, exporters, and a versioning system on top.

## Pipeline

```
ingest ──► RawDocument (Postgres)
              │  preprocess  (reuses app.nlp pipeline + new fact/issue/ruling segmenter)
              ▼
        CorpusRecord (standardized schema, Postgres JSONB)
              │  embed  (reuses app.embeddings encoder, 384-d MiniLM)
              ▼
        export ──► dataset/versions/<vX.Y.Z>/{data.jsonl, data.csv, data.parquet, manifest.json}
```

## CLI

```bash
pip install -e .            # exposes the `levcorpus` command
levcorpus init-db

# 1. collect
levcorpus ingest --source courtlistener --court ca9 --query asylum --limit 50
levcorpus ingest --source public-domain --path data/sample_opinions

# 2. structured extraction + auto annotation
levcorpus preprocess

# 3. sentence-transformer embeddings per case
levcorpus embed

# 4. standardized, versioned export
levcorpus export --formats jsonl,csv,parquet --bump minor --note "first ca9 asylum slice"

levcorpus versions          # list dataset versions + reproducibility logs
```

## Standardized schema (v1)

Canonical record defined in [`levcorpus/schema.py`](levcorpus/schema.py); JSON Schema mirror in
[`schemas/dataset_v1.schema.json`](schemas/dataset_v1.schema.json). Key fields:

| group | fields |
|---|---|
| identity | `record_id`, `source`, `source_url`, `external_id`, `license` |
| metadata | `case_name`, `court`, `jurisdiction`, `judge`, `judge_id`, `decided`, `parties`, `citations` |
| extracted | `facts_summary`, `legal_issue`, `ruling`, `text_sha256` |
| annotations | `outcome`, `case_type`, `topic`, `sentiment_proxy`, `decision_direction` |
| bias research | `judge_id`, `jurisdiction`, `decision_direction`, `embedding` (case-similarity vector) |
| provenance | `schema_version`, `dataset_version`, `ingested_at`, `embedding_model` |

## Versioning & reproducibility

Each `export` writes an immutable version directory with a `manifest.json` containing: semantic
version, schema version + **diff vs. previous version**, row count, a content hash (deterministic over
record hashes), the exact CLI invocation + resolved config (the **reproducibility log**), and the git
commit if available. A top-level `dataset/registry.json` and `dataset/CHANGELOG.md` index all versions.

## Notes on label quality

- `outcome` / `decision_direction` come from disposition-cue heuristics (or the optional trained
  classifier in the backend) — coarse and noisy by construction.
- `sentiment_proxy` is the backend's *tone-of-language* score. It is a **weak proxy** and labeled as
  such in every record (`annotations.sentiment_proxy_note`).
- `facts_summary` / `legal_issue` / `ruling` are extractive heuristics over opinion structure, not
  abstractive summaries.
