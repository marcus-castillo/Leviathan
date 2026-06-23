.PHONY: up down seed embeddings test logs

up:        ## Build and start the full stack
	docker compose up --build -d

down:      ## Stop the stack
	docker compose down

seed:      ## Load the bundled example dataset + analyze it
	docker compose exec backend python -m scripts.load_example_dataset

embeddings: ## (Re)compute analyses + embeddings for opinions missing them
	docker compose exec backend python -m scripts.build_embeddings

test:      ## Run backend unit tests (no DB/model downloads needed)
	docker compose exec backend pytest -q

logs:      ## Tail backend logs
	docker compose logs -f backend

# --- Corpus dataset builder (levcorpus) ---
corpus-build: ## End-to-end: ingest sample -> preprocess -> embed -> export a version
	docker compose --profile tools run --rm corpus init-db
	docker compose --profile tools run --rm corpus ingest --source public-domain --path data/sample_opinions
	docker compose --profile tools run --rm corpus preprocess
	docker compose --profile tools run --rm corpus embed
	docker compose --profile tools run --rm corpus export --bump minor --note "make corpus-build"

corpus-versions: ## List released dataset versions
	docker compose --profile tools run --rm corpus versions

corpus-test: ## Run levcorpus unit tests (no DB needed)
	docker compose --profile tools run --rm --entrypoint pytest corpus -q

# --- Graph layer (Neo4j) ---
graph-up: ## Start Neo4j + graph API + graph frontend
	docker compose up --build -d neo4j graph-api graph-frontend

graph-load: ## Load the example citation graph and compute influence metrics
	docker compose exec graph-api python -m scripts.load_example_graph
	docker compose exec graph-api python -m scripts.compute_metrics

graph-test: ## Run graph analytics tests (no Neo4j needed)
	docker compose run --rm --entrypoint pytest graph-api -q

# --- SCOTUS platform ---
scotus-up: ## Start the SCOTUS API + dashboard
	docker compose up --build -d scotus-api scotus-frontend

scotus-load: ## Load + segment the example corpus and build justice embeddings
	docker compose exec scotus-api python -m scripts.load_example_corpus
	docker compose exec scotus-api python -m scripts.build_justice_embeddings

scotus-test: ## Run SCOTUS NLP tests (no DB / encoder needed)
	docker compose run --rm --entrypoint pytest scotus-api -q
