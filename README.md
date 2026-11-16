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

Configure the following Secrets in your Hugging Face Space:

- `GEMINI_API_KEY`
- `QDRANT_URL`
- `QDRANT_API_KEY`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`

Neo4j configuration is read exclusively from these three `NEO4J_*` variables
(including a local `.env` file). Startup raises a `ValueError` naming any missing
variables before loading retrieval models. Constructor credential overrides are
no longer supported.

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
with `streamlit run app.py`. Pipeline modules use standard Python logging;
retrieval details are logged at DEBUG and attempt status at INFO.
