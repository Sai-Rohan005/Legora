"""FastAPI contracts and lifecycle tests with no live services or model loading."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import sleep
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from legora.config import ClientSettings, Settings


@pytest.fixture
def settings() -> Settings:
    """Use explicit fake credentials instead of the developer's .env file."""
    return Settings(
        _env_file=None, gemini_api_key="test-gemini", qdrant_url="http://qdrant.invalid",
        neo4j_uri="bolt://neo4j.invalid", neo4j_username="test-user",
        neo4j_password="test-password", kanoon_token="test-kanoon",
        external_timeout_seconds=0.05,
    )


@pytest.fixture
def pipeline() -> Mock:
    """Return an otherwise realistic result containing a non-JSON vector point."""
    pipeline = Mock()
    pipeline.llm.model = "test-model"
    point = SimpleNamespace(payload={"chunk_id": "BNS-303", "document": "BNS"})
    pipeline.search.return_value = {
        "answer": "A test answer grounded in the supplied sources.",
        "retrieval": {
            "statutory_results": [point], "vector_results": [point, point],
            "node_ids": ["BNS-303"], "graph_context": {},
            "judgments": [{"tid": "123", "title": "Test judgment"}],
        },
        "evaluation": {"overall_score": 90, "failure_stage": None}, "attempts": 2,
        "latency_ms": {"analysis": 1.1, "retrieval": 2.2, "rerank": 3.3, "graph": 4.4, "generation": 5.5, "judge": 6.6},
    }
    return pipeline


def test_query_contract_and_single_startup(settings: Settings, pipeline: Mock) -> None:
    """Load a single pipeline during lifespan and close it exactly once."""
    factory = Mock(return_value=pipeline)
    application = create_app(factory, settings)
    factory.assert_not_called()
    with TestClient(application) as client:
        for _ in range(2):
            response = client.post("/query", json={"query": "  Explain theft.  "})
            assert response.status_code == 200
        factory.assert_called_once_with()
        pipeline.close.assert_not_called()
    pipeline.close.assert_called_once_with()
    pipeline.search.assert_called_with(
        "Explain theft.", top_k=None, include_graph=True, include_judgments=True,
    )
    body = response.json()
    assert set(body) == {"answer", "citations", "retrieval_debug", "evaluation", "attempts", "latency_ms", "unsupported_citations", "citation_precision", "citation_checks"}
    assert body["retrieval_debug"] == {"vector_hits": 2, "reranked": 1, "node_ids": ["BNS-303"]}
    assert body["evaluation"] == {"score": 90, "stage": None}
    assert body["attempts"] == 2
    assert body["latency_ms"]["judge"] == 6.6
    assert body["citations"][0]["id"] == "BNS-303"
    assert body["citations"][1]["url"] == "https://indiankanoon.org/doc/123/"


def test_query_options_are_forwarded(settings: Settings, pipeline: Mock) -> None:
    """All optional controls reach the pipeline without UI-specific defaults."""
    with TestClient(create_app(lambda: pipeline, settings)) as client:
        response = client.post("/query", json={
            "query": "question", "top_k": 12, "include_graph": False, "include_judgments": False,
        })
    assert response.status_code == 200
    pipeline.search.assert_called_once_with(
        "question", top_k=12, include_graph=False, include_judgments=False,
    )


@pytest.mark.parametrize("body", [
    {}, {"query": ""}, {"query": "   "}, {"query": 1}, {"query": "q", "top_k": 0},
    {"query": "q", "top_k": 101}, {"query": "q", "top_k": True},
    {"query": "q", "include_graph": "false"}, {"query": "q", "unknown": True},
])
def test_request_validation(body: dict, settings: Settings, pipeline: Mock) -> None:
    """Invalid inputs receive 422 before pipeline execution, with no echoed input."""
    with TestClient(create_app(lambda: pipeline, settings)) as client:
        response = client.post("/query", json=body)
    assert response.status_code == 422
    pipeline.search.assert_not_called()
    assert "input" not in response.text


@pytest.mark.parametrize("error", [RuntimeError("secret-key traceback"), TimeoutError("secret-key")])
def test_upstream_failures_are_safe_502(error: Exception, settings: Settings, pipeline: Mock) -> None:
    """Do not return stack traces, SDK messages, or credentials on failures."""
    pipeline.search.side_effect = error
    with TestClient(create_app(lambda: pipeline, settings)) as client:
        response = client.post("/query", json={"query": "question"})
    assert response.status_code == 502
    assert "secret-key" not in response.text
    assert "traceback" not in response.text.lower()


def test_bad_pipeline_output_is_safe_502(settings: Settings, pipeline: Mock) -> None:
    """Malformed upstream results cannot produce unvalidated public responses."""
    result = deepcopy(pipeline.search.return_value)
    result["evaluation"]["overall_score"] = 500
    pipeline.search.return_value = result
    with TestClient(create_app(lambda: pipeline, settings)) as client:
        response = client.post("/query", json={"query": "question"})
    assert response.status_code == 502
    assert set(response.json()) == {"detail"}


def test_queries_are_serialized(settings: Settings, pipeline: Mock) -> None:
    """Concurrent HTTP requests cannot interleave mutable pipeline state."""
    active = 0
    maximum = 0
    guard = Lock()
    result = pipeline.search.return_value

    def search(*args: object, **kwargs: object) -> dict:
        """Track simultaneous pipeline execution while another request queues."""
        nonlocal active, maximum
        with guard:
            active += 1
            maximum = max(maximum, active)
        sleep(0.02)
        with guard:
            active -= 1
        return result

    pipeline.search.side_effect = search
    with TestClient(create_app(lambda: pipeline, settings)) as client:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: client.post("/query", json={"query": "question"}), range(2)))
    assert all(response.status_code == 200 for response in responses)
    assert maximum == 1


def test_queue_wait_has_deadline(settings: Settings, pipeline: Mock) -> None:
    """A busy model worker returns a safe 502 when the queue deadline expires."""
    application = create_app(lambda: pipeline, settings.model_copy(update={"query_lock_timeout_seconds": 0.01}))
    with TestClient(application) as client:
        application.state.query_lock.acquire()
        try:
            response = client.post("/query", json={"query": "question"})
        finally:
            application.state.query_lock.release()
    assert response.status_code == 502
    pipeline.search.assert_not_called()


def test_health_checks_all_dependencies(settings: Settings, pipeline: Mock) -> None:
    """Successful health probes exercise all three existing clients."""
    with TestClient(create_app(lambda: pipeline, settings)) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert {name: item["status"] for name, item in response.json()["dependencies"].items()} == {
        "qdrant": "ok", "neo4j": "ok", "gemini": "ok",
    }
    pipeline.retriever.hybrid.vector_db.client.get_collections.assert_called_once_with()
    pipeline.retriever.hybrid.graph.run_query.assert_called_once_with("RETURN 1 AS ok")
    pipeline.llm.client.models.get.assert_called_once_with(model="test-model")


def test_health_reports_failure_and_timeout(settings: Settings, pipeline: Mock) -> None:
    """One failed or stalled dependency does not hide the other probe results."""
    pipeline.retriever.hybrid.vector_db.client.get_collections.side_effect = RuntimeError("secret-key")
    pipeline.llm.client.models.get.side_effect = lambda **kwargs: sleep(0.15)
    with TestClient(create_app(lambda: pipeline, settings)) as client:
        response = client.get("/health")
    assert response.status_code == 502
    assert response.json()["status"] == "degraded"
    assert {name: item["status"] for name, item in response.json()["dependencies"].items()} == {
        "qdrant": "error", "neo4j": "ok", "gemini": "timeout",
    }
    assert "secret-key" not in response.text
    pipeline.search.assert_not_called()


def test_streamlit_chat_calls_api(
    settings: Settings, pipeline: Mock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Drive the actual UI through its HTTP adapter into a TestClient API."""
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr("legora.api_client.get_client_settings", lambda: ClientSettings(_env_file=None))
    with TestClient(create_app(lambda: pipeline, settings)) as client:
        post = Mock(side_effect=lambda url, json, timeout: client.post("/query", json=json))
        monkeypatch.setattr("legora.api_client.requests.post", post)
        page = AppTest.from_file("app.py", default_timeout=20).run()
        assert not page.exception
        pipeline.search.assert_not_called()
        page.chat_input[0].set_value("Explain theft.").run()
        assert not page.exception
        assert page.session_state["chat_history"][-1]["content"] == pipeline.search.return_value["answer"]
        post.assert_called_once_with(
            "http://127.0.0.1:8000/query", json={"query": "Explain theft."}, timeout=180,
        )


def test_api_flags_unsupported_statutory_citations(settings: Settings, pipeline: Mock) -> None:
    """Expose precise unsupported IDs and per-citation status without raw prompts."""
    pipeline.search.return_value["answer"] = "Section 303 BNS and BNSS 999(2)."
    pipeline.search.return_value["evaluation"] = {"overall_score": 45, "failure_stage": "CITATION"}
    with TestClient(create_app(lambda: pipeline, settings)) as client:
        response = client.post("/query", json={"query": "question"})
    assert response.status_code == 200
    assert response.json()["unsupported_citations"] == ["BNSS-999(2)"]
    assert response.json()["citation_precision"] == 0.5
    assert [citation["status"] for citation in response.json()["citation_checks"]] == ["citation_supported", "citation_unsupported"]
    assert response.json()["evaluation"]["stage"] == "CITATION"
