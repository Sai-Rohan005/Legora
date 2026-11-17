"""Bounded query caches and retries for transient external read/generation failures."""

from collections import OrderedDict
from collections.abc import Callable
from copy import deepcopy
from threading import RLock
from typing import ParamSpec, TypeVar

import httpx
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_exponential

P = ParamSpec("P")
T = TypeVar("T")


def normalize_query(query: str) -> str:
    """Collapse whitespace while retaining legally meaningful letter case and punctuation."""
    return " ".join(query.split())


class QueryCache:
    """An instance-local, thread-safe LRU; values cannot be mutated by callers."""

    def __init__(self, capacity: int = 512) -> None:
        """Bound retention of potentially sensitive query data to process memory."""
        self.capacity = capacity
        self.enabled = False
        self.values: OrderedDict[tuple, object] = OrderedDict()
        self.lock = RLock()

    def get(self, key: tuple, compute: Callable[[], T]) -> T:
        """Cache successful computations only; disabled mode preserves original behavior."""
        if not self.enabled:
            return compute()
        with self.lock:
            if key not in self.values:
                value = compute()
                self.values[key] = deepcopy(value)
                if len(self.values) > self.capacity:
                    self.values.popitem(last=False)
            self.values.move_to_end(key)
            return deepcopy(self.values[key])

    def clear(self) -> None:
        """Remove values before a cold benchmark or a model/prompt change."""
        with self.lock:
            self.values.clear()


def transient_failure(error: BaseException) -> bool:
    """Retry connectivity, throttling and transient server failures, never auth/validation."""
    from google.genai.errors import APIError
    from neo4j.exceptions import ServiceUnavailable, SessionExpired, TransientError
    from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

    if isinstance(error, (TimeoutError, ConnectionError, httpx.TransportError, ServiceUnavailable, SessionExpired, TransientError)):
        return True
    if isinstance(error, APIError):
        return error.code in {408, 429, 500, 502, 503, 504}
    if isinstance(error, UnexpectedResponse):
        return error.status_code in {408, 429, 500, 502, 503, 504}
    if isinstance(error, ResponseHandlingException):
        return transient_failure(error.source)
    return False


def call_external(function: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    """Use three bounded attempts with 0.25/0.5-second backoff; SDKs bound each call."""
    return Retrying(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.25, max=2),
        retry=retry_if_exception(transient_failure), reraise=True,
    )(function, *args, **kwargs)
