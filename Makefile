PYTHON ?= $(if $(wildcard venv/bin/python),venv/bin/python,python3)

.PHONY: test lint typecheck ingest
lint:
	$(PYTHON) -m ruff check api legora eval scripts LegalRag/citation_check.py retrieval/lexical.py
	$(PYTHON) -m ruff check --select E9,F63,F7,F82 .

typecheck:
	$(PYTHON) -m mypy

ingest:
	sh scripts/ingest.sh

test:
	$(PYTHON) -m pytest --cov --cov-branch --cov-report=term-missing --cov-report=html:coverage/html --cov-report=json:coverage/coverage.json
