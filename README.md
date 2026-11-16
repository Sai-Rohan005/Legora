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

Run regression tests with `python -m unittest discover -s tests -v` and the UI
with `streamlit run app.py`.
