#!/bin/sh
# Run from any directory; Compose loads the project .env without sourcing shell code.
set -eu
cd "$(dirname "$0")/.."
docker compose up -d --wait qdrant neo4j
docker compose run --rm --build --no-deps api python -m scripts.ingest --data-dir /data/statutes "$@"
