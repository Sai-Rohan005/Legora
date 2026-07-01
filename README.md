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