"""HTTP UI behavior and timeout coverage without backend credentials."""

from unittest.mock import Mock

import pytest
import requests

from legora.api_client import query_api
from legora.config import ClientSettings


def test_ui_client_uses_configured_url_and_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """The UI uses only HTTP settings and validates the public API response."""
    configuration = ClientSettings(_env_file=None, api_base_url="http://example.invalid/api/", api_timeout_seconds=12)
    monkeypatch.setattr("legora.api_client.get_client_settings", lambda: configuration)
    response = Mock(status_code=200)
    response.json.return_value = {
        "answer": "answer", "citations": [],
        "retrieval_debug": {"vector_hits": 0, "reranked": 0, "node_ids": []},
        "evaluation": {"score": 90, "stage": None}, "attempts": 1,
        "latency_ms": {name: 0 for name in ("analysis", "retrieval", "rerank", "graph", "generation", "judge")},
    }
    post = Mock(return_value=response)
    monkeypatch.setattr("legora.api_client.requests.post", post)
    assert query_api("question")["answer"] == "answer"
    post.assert_called_once_with("http://example.invalid/api/query", json={"query": "question"}, timeout=12)


@pytest.mark.parametrize("error", [requests.Timeout("secret-key"), requests.ConnectionError("secret-key")])
def test_ui_hides_transport_details(error: Exception, monkeypatch: pytest.MonkeyPatch) -> None:
    """Connection failures must not expose request URLs, secrets, or stack traces."""
    monkeypatch.setattr("legora.api_client.get_client_settings", lambda: ClientSettings(_env_file=None))
    monkeypatch.setattr("legora.api_client.requests.post", Mock(side_effect=error))
    with pytest.raises(RuntimeError, match="unavailable") as caught:
        query_api("question")
    assert "secret-key" not in str(caught.value)


def test_ui_validation_error_is_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    """An API 422 gets a user-facing explanation without echoing its body."""
    monkeypatch.setattr("legora.api_client.get_client_settings", lambda: ClientSettings(_env_file=None))
    monkeypatch.setattr("legora.api_client.requests.post", Mock(return_value=Mock(status_code=422)))
    with pytest.raises(ValueError, match="rejected"):
        query_api(" ")
