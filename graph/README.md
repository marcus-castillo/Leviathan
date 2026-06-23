# Leviathan Graph (`graphapp`)

**Models judicial decisions as a citation graph and analyzes influence and statistical grouping —
with the same anti-overclaiming guardrails as the rest of Leviathan.**

> ⚠️ "Bias propagation" here means **statistical grouping of citation/topic patterns**, nothing more.
> The system does **not** assign ideology to any judge, does not infer intent, and does not claim a
> group is "liberal", "conservative", or "biased". Communities are graph artifacts (who cites whom,
> about what) that are sensitive to the corpus, the time window, and the clustering parameters. See
> [`../ETHICS.md`](../ETHICS.md).

## Graph model

```
(:Judge)                     (:Court)            (:LegalTopic)
    ▲                            ▲                     ▲
    │ AUTHORED_BY                │ IN_COURT            │ ABOUT_TOPIC
    │                            │                     │
  (:Case) ──CITES────────────► (:Case)
        ──OVERRULES──────────►
        ──FOLLOWS────────────►
        ──DISTINGUISHES──────►
```

| Node | Key | |
|---|---|---|
| `Case` | `id` | `case_name, decided, court, decision_direction` |
| `Judge` | `judge_id` | `display_name` |
| `Court` | `slug` | `name, jurisdiction` |
| `LegalTopic` | `name` | |

| Edge | From → To | Meaning |
|---|---|---|
| `CITES` | Case → Case | generic citation |
| `OVERRULES` | Case → Case | negative treatment |
| `FOLLOWS` | Case → Case | positive/adopting treatment |
| `DISTINGUISHES` | Case → Case | limits/distinguishes |
| `AUTHORED_BY` | Case → Judge | authorship |
| `IN_COURT` | Case → Court | helper |
| `ABOUT_TOPIC` | Case → LegalTopic | helper |

Cypher constraints in [`graphapp/schema.py`](graphapp/schema.py).

## Pipeline

1. **Construct** — [`build/pipeline.py`](graphapp/build/pipeline.py) ingests opinions (example JSONL, or
   the shared Postgres `opinions` table) and MERGEs nodes + typed citation edges. Edge *type* is
   detected from the language around each citation by [`build/citation_parser.py`](graphapp/build/citation_parser.py)
   (overrule / distinguish / follow / cite).
2. **Analyze** — `analysis/*` pull the relevant subgraph into NetworkX and compute:
   - **influence** — degree / PageRank / betweenness centrality + per-judge citation influence.
   - **clustering** — Louvain communities over the case citation network.
   - **statistical grouping** — judges grouped by topic+citation profile (KMeans), *labels are G1/G2…*, never ideological.
   - **temporal** — topic mix and most-cited precedents per era.
3. **Serve / visualize** — FastAPI → Next.js + Cytoscape.js.

## Run

Neo4j + the graph API are wired into the root `docker-compose.yml`:

```bash
docker compose up --build neo4j graph-api graph-frontend
docker compose exec graph-api python -m scripts.load_example_graph
docker compose exec graph-api python -m scripts.compute_metrics   # writes centrality back to nodes
# graph API   http://localhost:8001/docs
# graph UI    http://localhost:3001
# Neo4j browser http://localhost:7474  (neo4j / leviathan_graph)
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /graph/case/{id}` | ego-network around a case (citations in/out, typed edges) |
| `GET /graph/judge/{id}` | a judge's authored cases, influence scores, and influence paths |
| `GET /graph/cluster` | case communities + judge statistical grouping (+ caveats) |
| `GET /graph/network` | sampled network for the zoomable explorer |
| `GET /graph/temporal` | reasoning-evolution series |

## Why NetworkX for analytics

The analytics layer takes a plain `networkx.DiGraph`, so every metric is unit-testable without a
running database and we avoid a hard dependency on the Neo4j Graph Data Science plugin. The Neo4j
client simply hydrates the graph; results can optionally be written back to nodes.
