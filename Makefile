PYTHON ?= $(if $(wildcard venv/bin/python),venv/bin/python,python3)

.PHONY: test
test:
	$(PYTHON) -m pytest --cov --cov-branch --cov-report=term-missing --cov-report=html:coverage/html --cov-report=json:coverage/coverage.json
