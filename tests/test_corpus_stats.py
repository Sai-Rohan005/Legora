"""Verify measured corpus statistics without network calls or production fixtures."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.corpus_stats import collect_stats, graph_counts, vector_counts, write_report


def point(identifier: str | None, document: str | None = None) -> SimpleNamespace:
    """Represent a stored payload, including deliberately malformed rows."""
    return SimpleNamespace(payload={"chunk_id": identifier, "document": document})


def test_vector_scroll_counts_unique_chunks_duplicates_missing_and_unmapped() -> None:
    """All pages and legacy IDs count, while duplicate points do not inflate chunk totals."""
    client = Mock()
    client.scroll.side_effect = [
        ([point("BNS-303", "bns"), point("BNS-303", "bns"), point(None)], "next"),
        ([point("article_21"), point("unknown-id"), point("BNSS-45(2)", "bnss")], None),
    ]
    result = vector_counts(client, "legal_rag")
    assert result["stored_points"] == 6
    assert result["unique_chunks"] == 4
    assert result["duplicate_chunk_points"] == 1
    assert result["points_without_chunk_id"] == 1
    assert result["chunks_by_act"] == {"BNS": 1, "BNSS": 1, "BSA": 0, "Constitution": 1, "Unmapped": 1}
    assert client.scroll.call_args.kwargs["offset"] == "next"
    assert client.scroll.call_args.kwargs["with_vectors"] is False


def test_conflicting_chunk_metadata_is_not_reported_as_a_valid_total() -> None:
    """A duplicate ID assigned to two acts is data corruption, not two distinct chunks."""
    client = Mock()
    client.scroll.return_value = ([point("BNS-303", "bns"), point("BNS-303", "bsa")], None)
    with pytest.raises(ValueError):
        vector_counts(client, "legal_rag")


def test_graph_counts_merge_metadata_aliases_and_count_edges_by_source() -> None:
    """Graph counts include unmapped nodes and actual directed edges, without deduping inverses."""
    graph = Mock()
    graph.run_query.side_effect = [
        [{"document": "BNS", "count": 12}, {"document": "CONSTITUTION", "count": 3}, {"document": "CONST", "count": 2}, {"document": None, "count": 1}],
        [{"document": "BNS", "count": 20}, {"document": "CONSTITUTION", "count": 5}],
    ]
    result = graph_counts(graph)
    assert result["nodes_by_act"]["Constitution"] == 5
    assert result["nodes_by_act"]["Unmapped"] == 1
    assert result["edges_by_act"]["BNS"] == 20
    assert "a.document AS document" in graph.run_query.call_args.args[0]


@pytest.mark.parametrize("invalid", [-1, True, 2.5, "3"])
def test_invalid_graph_counts_are_rejected(invalid: object) -> None:
    """Malformed upstream counts cannot appear as measured corpus statistics."""
    graph = Mock()
    graph.run_query.return_value = [{"document": "BNS", "count": invalid}]
    with pytest.raises(ValueError):
        graph_counts(graph)


def test_unavailable_dependencies_produce_nulls_without_secret_messages(tmp_path: Path) -> None:
    """Failed reads must not imply an empty corpus or leak endpoint credentials."""
    result = collect_stats(Mock(side_effect=ValueError("secret endpoint")), Mock(side_effect=ConnectionError("secret password")), "legal_rag")
    assert result["status"] == "unavailable"
    assert all(value is None for value in result["totals"].values())
    report = write_report(tmp_path, result)
    assert "Not measured" in report and "| Total |" in report
    assert "secret" not in report and "secret" not in (tmp_path / "corpus_stats.json").read_text()
    assert json.loads((tmp_path / "corpus_stats.json").read_text())["totals"]["chunks"] is None


def test_partial_measurement_preserves_successful_zero_counts_and_closes_client() -> None:
    """An actually empty store reports zero; an inaccessible other store remains unknown."""
    client = Mock()
    client.scroll.return_value = ([], None)
    result = collect_stats(lambda: client, Mock(side_effect=ValueError()), "legal_rag")
    assert result["status"] == "partial"
    assert result["totals"] == {"chunks": 0, "graph_nodes": None, "graph_edges": None}
    client.close.assert_called_once_with()


def test_complete_live_shaped_counts_compute_totals_without_model_loading() -> None:
    """Only successful reads from both stores produce a completed report."""
    client, graph = Mock(), Mock()
    client.scroll.return_value = ([point("BSA-115", "bsa")], None)
    graph.run_query.side_effect = [[{"document": "BSA", "count": 4}], [{"document": "BSA", "count": 6}]]
    result = collect_stats(lambda: client, lambda: graph, "legal_rag")
    assert result["status"] == "completed"
    assert result["totals"] == {"chunks": 1, "graph_nodes": 4, "graph_edges": 6}
    graph.close.assert_called_once_with()


def test_failed_scroll_closes_client_without_reporting_partial_counts() -> None:
    """A paginated failure does not publish the first page as the whole corpus."""
    client = Mock()
    client.scroll.side_effect = [([point("BNS-303", "bns")], "next"), ValueError("failed page")]
    result = collect_stats(lambda: client, Mock(side_effect=ValueError()), "legal_rag")
    assert result["totals"]["chunks"] is None
    client.close.assert_called_once_with()
