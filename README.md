---
title: Legora
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Legora

Legora is an AI-powered Legal Retrieval-Augmented Generation (RAG) system designed to answer legal questions using semantic search, graph retrieval, and Large Language Models.

## Features

- Retrieval-Augmented Generation (RAG)
- Semantic Search using Sentence Transformers
- Graph Retrieval using Neo4j
- Vector Search using Qdrant
- Google Gemini Integration
- Streamlit-based User Interface

## Tech Stack

- Python
- Streamlit
- Sentence Transformers
- Transformers
- Qdrant
- Neo4j
- Google Gemini
- Docker

## Environment Variables

Copy `.env.example` to `.env` and replace the placeholder credentials, or set
the same variables in your deployment environment. `legora/config.py` uses
pydantic-settings: environment variables override the project-root `.env` file,
variable names are case-insensitive, and settings are cached for the process.
Restart the app after changing configuration. Imports do not load clients.

Required: `GEMINI_API_KEY`, `QDRANT_URL`, `NEO4J_URI`, `NEO4J_USERNAME`,
`NEO4J_PASSWORD`, and `KANOON_TOKEN`. `QDRANT_API_KEY` is optional for a local
unauthenticated instance. Neo4j and Qdrant connection configuration comes from
settings; configure local URLs explicitly. Missing or blank required settings
fail validation before retrieval models load. Validation errors hide input values.

`GEMINI_MODEL` controls all Gemini clients (default `gemini-2.5-flash-lite`).
Retrieval defaults are `TOP_K=30`, `RERANK_K=5`, and `JUDGMENT_K=5`.
`PASS_THRESHOLD=80` uses the evaluator's 0–100 scale; `MAX_ATTEMPTS=3` is the
maximum total attempts. All candidate limits and the retry budget must be positive.

`LOG_LEVEL` defaults to `INFO`. The application configures newline-delimited JSON
console logs with a fresh `request_id` per `RAGPipeline.search()` call. Retries
share that ID and carry a 1-based `attempt`; context is restored when the query
finishes or raises. Stage events include `stage`, `latency_ms`, `candidate_count`,
`status`, and `error_type`. Counts are unique vector results, retained rerank
results, expanded graph roots, or fetched judgments, depending on the stage;
generation and evaluation use the number of supplied statutory/judgment sources.
Counts are null before output is available or when not applicable (query analysis).
Query totals report final source counts. Latencies use a monotonic timer. A stage
status describes execution success, not the evaluator's pass/fail decision.

Logs omit questions, prompts, keys, and raw exception messages. Secrets use
Pydantic `SecretStr`; stage failures log only the exception class. SDK HTTP debug
logging is suppressed. To correlate a query, filter JSON events by `request_id`.

Hierarchy edges use `(child)-[:BELONGS_TO]->(parent)`. Existing BNS graphs built
with only `HAS_*` edges need the inverse edges added once before BNS hierarchy
retrieval works. On a backed-up database, run:

```cypher
MATCH (parent)-[r]->(child)
WHERE type(r) IN ['HAS_PART', 'HAS_CHAPTER', 'HAS_SECTION', 'HAS_CLAUSE',
                 'HAS_SUBCLAUSE', 'HAS_ROMANCLAUSE', 'HAS_EXPLANATION',
                 'HAS_ILLUSTRATION']
  AND parent.id STARTS WITH 'BNS'
  AND child.id STARTS WITH 'BNS'
MERGE (child)-[:BELONGS_TO]->(parent);
```

## API and UI

Install dependencies with `python -m pip install -r requirements.txt`. Start the
API and Streamlit in separate terminals:

```bash
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
streamlit run app.py
```

The API lifespan loads one pipeline (including the embedder and reranker) per
worker and closes its clients on shutdown. Queries are serialized per worker
because the pipeline holds mutable retry state. More Uvicorn workers each load
their own models. The Docker command starts an internal API alongside the UI;
only the Streamlit port is exposed.

Streamlit uses `API_BASE_URL` (default `http://127.0.0.1:8000`) and
`API_TIMEOUT_SECONDS` (default 180). It needs no backend credentials or models.
Set `API_BASE_URL` to the backend's reachable address when running separately.
API startup still requires all backend settings listed above.

`POST /query` accepts `query` (1–20,000 characters), optional `top_k` (1–100),
`include_graph` and `include_judgments` (both default true). Disabling a source
skips its external calls. For example:

```bash
curl -X POST http://127.0.0.1:8000/query -H 'Content-Type: application/json' \
  -d '{"query":"What does Article 21 protect?","top_k":10,"include_judgments":false}'
```

The response contains `answer`, `citations`, `retrieval_debug` (`vector_hits`
and `reranked` counts plus `node_ids` from the final attempt), `evaluation`
(`score`, `stage`), `attempts`, and `latency_ms` (`analysis`, `retrieval`,
`rerank`, `graph`, `generation`, `judge`). Citations identify retained retrieval
sources. Timings are measured and summed across retries: retrieval covers vector
search plus judgment retrieval; analysis, reranking, graph, generation, and judging
are separate. Skipped stages have zero duration. Exhausted evaluation retries
return the last answer, score, and failure stage.

`GET /health` probes Qdrant collections, a Neo4j `RETURN 1` query, and Gemini
model metadata using the startup clients. It returns status and measured latency
for each dependency, with HTTP 200 when all are reachable and 502 otherwise.
The Gemini probe checks connectivity/authentication, not generation quota.

`EXTERNAL_TIMEOUT_SECONDS` (default 30) configures Gemini, Qdrant, Neo4j, and
Indian Kanoon calls; health probes also enforce a client-side deadline. Gemini
SDK retries are disabled. Neo4j has connection/acquisition/write and query
execution timeouts. `QUERY_LOCK_TIMEOUT_SECONDS` (default 180) bounds the wait
for the shared pipeline. These are per-call/queue deadlines, not a total query
budget; retries and multiple external calls can take longer in aggregate.

Invalid request bodies return 422. Backend failures, upstream timeouts, and
expired queue waits return 502 with generic messages. No raw SDK errors, API
keys, graph objects, or stack traces appear in API error responses.

Run tests with `python -m pytest`. Tests use FastAPI TestClient and mocked
pipelines/SDK clients, including startup lifecycle, validation, optional sources,
health failures/timeouts, serialization, and Streamlit HTTP client behavior.
