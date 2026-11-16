"""JSON logging with request-local correlation and stage timing."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
attempt_number: ContextVar[int] = ContextVar("attempt_number", default=0)
logger = logging.getLogger(__name__)


class JsonFormatter(logging.Formatter):
    """Serialize application metadata without arbitrary extras or exceptions."""

    def format(self, record: logging.LogRecord) -> str:
        """Render one JSON object; exception messages may contain credentials."""
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id.get(),
            "attempt": attempt_number.get(),
        }
        for name in ("stage", "latency_ms", "candidate_count", "status", "error_type"):
            if hasattr(record, name):
                payload[name] = getattr(record, name)
        return json.dumps(payload)


def setup_logging(level: str = "INFO") -> None:
    """Install one JSON console handler, including across Streamlit reruns."""
    root = logging.getLogger()
    if not any(getattr(handler, "_legora_json", False) for handler in root.handlers):
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        handler._legora_json = True
        root.handlers[:] = [handler]
    root.setLevel(level)
    # HTTP request URLs and SDK diagnostics can contain credentials.
    for name in ("httpx", "httpcore", "urllib3", "google", "neo4j"):
        logging.getLogger(name).setLevel(logging.WARNING)


@contextmanager
def query_context() -> Iterator[str]:
    """Assign a fresh ID and restore the caller's context even on failure."""
    identifier = uuid4().hex
    request_token = request_id.set(identifier)
    attempt_token = attempt_number.set(0)
    try:
        yield identifier
    finally:
        attempt_number.reset(attempt_token)
        request_id.reset(request_token)


@dataclass
class StageMetrics:
    """Candidate count filled in by the stage when its output is available."""

    candidate_count: int | None = None


@contextmanager
def log_stage(name: str, candidate_count: int | None = None) -> Iterator[StageMetrics]:
    """Log actual elapsed time and output count, including failed stages."""
    metrics = StageMetrics(candidate_count)
    started = perf_counter()
    status = "ok"
    error_type = None
    try:
        yield metrics
    except BaseException as error:
        status = "error"
        error_type = type(error).__name__
        raise
    finally:
        logger.log(
            logging.ERROR if status == "error" else logging.INFO,
            "Stage completed",
            extra={
                "stage": name,
                "latency_ms": round((perf_counter() - started) * 1000, 3),
                "candidate_count": metrics.candidate_count,
                "status": status,
                "error_type": error_type,
            },
        )
