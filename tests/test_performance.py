"""Offline equivalence, caching, concurrency, retry and profiling regression checks."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
import tenacity

from eval.profile_pipeline import main, percentile, provision_recall, render_report, run_profiles
from legora.performance import QueryCache, call_external, normalize_query, transient_failure
from retrieval.hybrid_retrieval import HybridRetriever
from tests.test_answer_eval import gold


def test_query_cache_normalization_eviction_isolation_and_failures() -> None:
    """Only successful normalized computations are retained; returned mutations are isolated."""
    cache = QueryCache(capacity=2)
    cache.enabled = True
    compute = Mock(return_value=[1])
    key = (normalize_query(" Section  303\nBNS "),)
    cache.get(key, compute).append(2)
    assert cache.get(("Section 303 BNS",), compute) == [1]
    assert compute.call_count == 1
    assert normalize_query("303(a)") != normalize_query("303(A)")
    cache.get(("b",), compute)
    cache.get(key, compute)
    cache.get(("c",), compute)
    assert ("b",) not in cache.values
    failing = Mock(side_effect=ValueError("Bad response"))
    with pytest.raises(ValueError):
        cache.get(("failed",), failing)
    assert ("failed",) not in cache.values
    cache.clear()
    assert not cache.values


def test_cache_single_flight_concurrent_identical_requests() -> None:
    """A shared cache computes once, even when several request threads miss together."""
    cache = QueryCache()
    cache.enabled = True
    compute = Mock(return_value=[42])
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(lambda _: cache.get(("query",), compute), range(4)))
    assert results == [[42]] * 4 and compute.call_count == 1


def test_embedding_cache_uses_normalized_query_and_keeps_instruction() -> None:
    """The real embedder wrapper avoids repeat encoding without loading a model."""
    from db.embedder import LegalEmbedder

    embedder = LegalEmbedder.__new__(LegalEmbedder)
    embedder.model_name, embedder.model = "test-model", Mock()
    embedder.query_cache = QueryCache()
    embedder.query_cache.enabled = True
    embedder.model.encode.return_value = [1, 2]
    assert embedder.embed_query("  Section 303\nBNS") == embedder.embed_query("Section 303 BNS")
    assert embedder.model.encode.call_count == 1
    assert embedder.model.encode.call_args.args[0].endswith("passages: Section 303 BNS")


def test_analysis_cache_key_includes_seed_model_prompt() -> None:
    """Normalization reuses analysis, but model/prompt/seed changes cannot reuse stale metadata."""
    from LegalRag.query_analyser import Analyser

    analyser = Analyser.__new__(Analyser)
    analyser.model, analyser.SYSTEM_PROMPT = "model", "prompt"
    analyser.query_cache = QueryCache()
    analyser.query_cache.enabled = True
    analyser._analyze_query = Mock(return_value={"acts": ["BNS"]})
    analyser.analyze_query(" Theft\nquestion ", seed=1)
    analyser.analyze_query("Theft question", seed=1)
    assert analyser._analyze_query.call_count == 1
    analyser.analyze_query("Theft question", seed=2)
    analyser.model = "other-model"
    analyser.analyze_query("Theft question", seed=2)
    analyser.SYSTEM_PROMPT = "other-prompt"
    analyser.analyze_query("Theft question", seed=2)
    assert analyser._analyze_query.call_count == 4


def test_concurrent_vector_io_overlaps_but_preserves_order_and_ties() -> None:
    """A barrier requires three searches in flight; ordered merge retains baseline ranking."""
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.vector_search_workers = 3
    retriever.embedder = Mock()
    retriever.embedder.embed_query.side_effect = lambda query: query
    barrier = Barrier(3)
    points = [SimpleNamespace(payload={"chunk_id": "BNS-303"}, score=1) for _ in range(3)]

    def search(query_vector: str, document: str, limit: int) -> SimpleNamespace:
        """Synchronize external-call boundaries, never mock result merging."""
        barrier.wait(timeout=3)
        assert document == "bns" and limit == 5
        return SimpleNamespace(points=[points[int(query_vector)]])

    retriever.vector_db = Mock()
    retriever.vector_db.search_with_filter.side_effect = search
    results = retriever.search_queries(["0", "1", "2"], "bns", 5)
    assert all(result is expected for result, expected in zip(results, points))
    assert retriever.dedupe_points(results) == [points[0]]
    retriever.vector_search_workers = 1
    retriever.vector_search_filtered = Mock(side_effect=[[point] for point in points])
    assert retriever.search_queries(["0", "1", "2"], "bns", 5) == results


def test_parallel_search_failures_propagate_without_partial_hits() -> None:
    """An upstream error cannot silently turn a partial candidate pool into a successful answer."""
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.vector_search_workers = 2
    retriever.embedder = Mock()
    retriever.vector_db = Mock()
    retriever.vector_db.search_with_filter.side_effect = ValueError("upstream failure")
    with pytest.raises(ValueError):
        retriever.search_queries(["one", "two"], None, 5)


def test_batch_graph_preserves_legacy_structure_with_one_call_instead_of_six() -> None:
    """Grouping returns the same ancestor/child/reference records, including missing nodes."""
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.graph = Mock()
    retriever.get_ancestors = Mock(side_effect=lambda identifier: [{"p": identifier + "-parent"}])
    retriever.get_children = Mock(side_effect=lambda identifier: [{"p": identifier + "-child"}])
    retriever.get_references = Mock(return_value=[])
    expected = retriever.expand_graph(["BNS-1", "BNS-2"])
    assert sum(method.call_count for method in (retriever.get_ancestors, retriever.get_children, retriever.get_references)) == 6
    retriever.graph.run_query.return_value = [
        {"id": identifier, "kind": kind, "value": identifier + suffix}
        for identifier in ("BNS-1", "BNS-2") for kind, suffix in (("ancestors", "-parent"), ("children", "-child"))
    ]
    retriever.batch_graph_expansion = True
    actual = retriever.expand_graph(["BNS-1", "BNS-2", "BNS-1", "missing"])
    assert {key: actual[key] for key in expected} == expected
    assert actual["missing"] == {"ancestors": [], "children": [], "references": []}
    assert retriever.graph.run_query.call_count == 1
    query, parameters = retriever.graph.run_query.call_args.args
    assert "UNWIND $ids" in query and "UNION ALL" in query
    assert "<-[:BELONGS_TO*0..10]" in query and "-[:REFERENCES]->" in query
    assert parameters == {"ids": ["BNS-1", "BNS-2", "missing"]}
    retriever.graph.run_query.reset_mock()
    assert retriever.expand_graph([]) == {}
    retriever.graph.run_query.assert_not_called()


def test_backoff_is_bounded_and_only_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercise retry classification and attempts while replacing only real sleep."""
    delays = []
    original = tenacity.Retrying
    monkeypatch.setattr("legora.performance.Retrying", lambda **kwargs: original(**kwargs, sleep=delays.append))
    function = Mock(side_effect=[httpx.ConnectError("unavailable"), TimeoutError(), "ok"])
    assert call_external(function) == "ok"
    assert function.call_count == 3 and delays == [.25, .5]
    function = Mock(side_effect=ValueError("invalid query"))
    with pytest.raises(ValueError):
        call_external(function)
    assert function.call_count == 1
    function = Mock(side_effect=TimeoutError())
    with pytest.raises(TimeoutError):
        call_external(function)
    assert function.call_count == 3


def test_authentication_is_not_retryable() -> None:
    """Permanent SDK errors fail immediately instead of consuming repeated quotas."""
    from google.genai.errors import APIError
    from neo4j.exceptions import ServiceUnavailable
    from qdrant_client.http.exceptions import UnexpectedResponse

    assert transient_failure(APIError(429, {}))
    assert not transient_failure(APIError(401, {}))
    assert transient_failure(ServiceUnavailable("down"))
    assert transient_failure(UnexpectedResponse(503, "down", b"", {}))
    assert not transient_failure(UnexpectedResponse(400, "bad", b"", {}))


def test_profile_has_paired_modes_percentiles_and_quality_regression_warning() -> None:
    """Report synthetic test measurements only in memory; regressions are explicitly rejected."""
    pipeline = Mock()
    pipeline.search.return_value = {
        "answer": "Section 303 BNS", "retrieval": {"statutory_results": [{"chunk_id": "BNS-303"}]},
        "stage_latency_ms": {stage: 10 for stage in ("analysis", "embedding", "vector_search", "rerank", "neo4j", "generation", "judge")}, "attempts": 1,
    }
    rows = run_profiles([gold("a"), gold("b")], pipeline)
    assert len(rows) == 6 and pipeline.search.call_count == 6
    assert pipeline.retriever.hybrid.embedder.query_cache.clear.call_count == 2
    assert percentile([1, 2, 3, 4], .95) == pytest.approx(3.85)
    rows[2]["recall_at_5"] = 0
    report = render_report(rows, 2, 42, 100)
    assert "REGRESSION: recall_at_5" in report and "Before p95 ms" in report
    assert "Judge skipping: NOT MEASURED" in report
    with pytest.raises(ValueError):
        render_report(rows[:-1], 2, 42, 100)


def test_profile_recall_uses_top_five_root_matches_and_excludes_out_of_scope() -> None:
    """Retrieval quality is measured from actual retained sources, not answer mentions."""
    result = {"retrieval": {"statutory_results": [{"chunk_id": f"BNS-{number}(2)"} for number in (1, 2, 3, 4, 5, 303)]}}
    assert provision_recall(gold("a"), result) == 0
    assert provision_recall(gold("outside", answerable=False), result) is None
    result["retrieval"]["statutory_results"].insert(0, {"chunk_id": "BNS-303(2)"})
    assert provision_recall(gold("a"), result) == 1


def test_profile_empty_gold_gate_avoids_startup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unavailable corpus/labels must never produce invented benchmark percentiles."""
    factory = Mock(side_effect=AssertionError("must not initialize"))
    monkeypatch.setattr("eval.profile_pipeline.load_pipeline", factory)
    monkeypatch.setattr("sys.argv", ["profile", "--gold", str(tmp_path / "missing.jsonl"), "--output-dir", str(tmp_path)])
    with pytest.raises(SystemExit):
        main()
    factory.assert_not_called()
    assert "not run" in (tmp_path / "latency.md").read_text()
    assert not (tmp_path / "latency.json").exists()


def test_judge_skip_flag_fails_before_model_loading(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unvalidated retrieval confidence must not bypass legal answer evaluation."""
    from LegalRag.rag_pipeline import RAGPipeline

    monkeypatch.setattr("LegalRag.rag_pipeline.get_settings", lambda: SimpleNamespace(skip_judge_high_confidence=True))
    loader = Mock(side_effect=AssertionError("No heavy startup"))
    monkeypatch.setattr("LegalRag.rag_pipeline.LegalRetriever", loader)
    with pytest.raises(ValueError, match="no quality loss"):
        RAGPipeline()
    loader.assert_not_called()


def test_real_vector_wrapper_records_embedding_separately() -> None:
    """Stage collection retains embedding so the profiler can exclude it from vector wall time."""
    from legora.logging import log_stage, query_context, stage_timings

    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.embedder = Mock()
    retriever.embedder.embed_query.return_value = [1, 2]
    retriever.vector_db = Mock()
    retriever.vector_db.search_with_filter.return_value.points = []
    with query_context(), log_stage("vector_search"):
        assert retriever.vector_search_filtered("query", "bns", 5) == []
        assert stage_timings.get()["embedding"] >= 0
    retriever.vector_db.search_with_filter.assert_called_once_with(query_vector=[1, 2], document="bns", limit=5)


def test_store_reads_apply_transient_retry_with_existing_parameters(monkeypatch: pytest.MonkeyPatch) -> None:
    """Actual Qdrant and Neo4j wrappers retry reads rather than dropping candidates/nodes."""
    from db.neo4j_store import Neo4jStore
    from db.vector_store import QdrantStore

    original = tenacity.Retrying
    monkeypatch.setattr("legora.performance.Retrying", lambda **kwargs: original(**kwargs, sleep=lambda _: None))
    vector = QdrantStore.__new__(QdrantStore)
    vector.collection_name, vector.exact_search, vector.client = "legal_rag", False, Mock()
    vector.client.query_points.side_effect = [TimeoutError(), SimpleNamespace(points=["hit"])]
    assert vector.search_with_filter([1], "bns", 5).points == ["hit"]
    assert vector.client.query_points.call_count == 2
    graph = Neo4jStore.__new__(Neo4jStore)
    record = Mock()
    record.data.return_value = {"node": "value"}
    graph.execute = Mock(side_effect=[TimeoutError(), [record]])
    assert graph.run_query("RETURN $value", {"value": 1}) == [{"node": "value"}]
    assert graph.execute.call_count == 2
    assert graph.execute.call_args.args == ("RETURN $value", {"value": 1})
