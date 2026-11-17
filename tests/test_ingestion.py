"""Exercise real statute parsing, graph building and ingestion without external services."""

from pathlib import Path
from unittest.mock import Mock
from uuid import UUID

import numpy as np
import pytest

from scripts.ingest import ingest_corpus, main, prepare_corpus, source_text

FIXTURES = Path(__file__).parent / "fixtures"


def clients() -> tuple[Mock, Mock, Mock]:
    """Replace only embedding computation and persistence clients."""
    embedder, vectors, graph = Mock(), Mock(), Mock()
    embedder.vector_size.return_value = 2
    embedder.embed.side_effect = lambda texts: np.ones((len(texts), 2))
    return embedder, vectors, graph


def test_real_corpus_and_graph_builders_use_same_documents_with_bounded_batches() -> None:
    """All four statutes reach vectors and graph with stable globally unique chunk identities."""
    corpus = prepare_corpus(FIXTURES)
    embedder, vectors, graph = clients()
    ingest_corpus(corpus, embedder, vectors, graph, batch_size=3)
    assert {statute.name for statute in corpus} == {"bns", "bnss", "bsa", "constitution"}
    assert all(len(call.args[0]) <= 3 for call in embedder.embed.call_args_list)
    points = [point for call in vectors.upsert_points.call_args_list for point in call.args[0]]
    assert len(points) == sum(len(statute.chunks) for statute in corpus)
    assert len({point["id"] for point in points}) == len(points)
    assert all(UUID(point["id"]).version == 5 for point in points)
    assert {"BNS-303", "BNSS-35", "BSA-2"} <= {point["payload"]["chunk_id"] for point in points}
    nodes = {call.kwargs.get("node_id", call.args[1] if call.args else "") for call in graph.merge_node.call_args_list}
    assert {"BNS-303", "BNSS-35", "BSA-2", "CONST-19"} <= nodes
    vectors.create_collection.assert_called_once_with(2)
    graph.create_constraints.assert_called_once_with()
    vectors.recreate_collection.assert_not_called()
    graph.clear_graph.assert_not_called()


def test_repeat_ingestion_keeps_uuid_ids_even_if_source_order_changes() -> None:
    """Reingestion upserts identical provision IDs rather than renumbering other statutes."""
    corpus = prepare_corpus(FIXTURES)
    embedder, vectors, graph = clients()
    ingest_corpus(corpus, embedder, vectors, graph)
    before = {point["payload"]["chunk_id"]: point["id"] for call in vectors.upsert_points.call_args_list for point in call.args[0]}
    vectors.upsert_points.reset_mock()
    ingest_corpus(list(reversed(corpus)), embedder, vectors, graph)
    after = {point["payload"]["chunk_id"]: point["id"] for call in vectors.upsert_points.call_args_list for point in call.args[0]}
    assert before == after


def test_embedding_count_mismatch_is_failure_instead_of_silent_zip_truncation() -> None:
    """No incomplete embedding batch is uploaded as if it succeeded."""
    corpus = prepare_corpus(FIXTURES)
    embedder, vectors, graph = clients()
    embedder.embed.side_effect = lambda texts: np.ones((len(texts) - 1, 2))
    with pytest.raises(ValueError, match="Embedding count"):
        ingest_corpus(corpus, embedder, vectors, graph)
    vectors.upsert_points.assert_not_called()


@pytest.mark.parametrize("batch_size", [0, -1])
def test_invalid_batch_size_never_mutates_stores(batch_size: int) -> None:
    """Invalid configuration fails before collection/graph creation."""
    embedder, vectors, graph = clients()
    with pytest.raises(ValueError):
        ingest_corpus([], embedder, vectors, graph, batch_size)
    vectors.create_collection.assert_not_called()
    graph.create_constraints.assert_not_called()


def test_source_text_prefers_reviewed_text_and_rejects_empty_or_missing(tmp_path: Path) -> None:
    """PDF extraction never replaces a reviewer-supplied UTF-8 source."""
    (tmp_path / "bns.txt").write_text("Reviewed statute text")
    (tmp_path / "bns.pdf").write_bytes(b"test-only-placeholder")
    assert source_text(tmp_path, "bns") == "Reviewed statute text"
    (tmp_path / "bns.txt").write_text(" \n")
    with pytest.raises(ValueError, match="Empty"):
        source_text(tmp_path, "bns")
    with pytest.raises(ValueError, match="Missing"):
        source_text(tmp_path, "bnss")


def test_pdf_extraction_rejects_scanned_pages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Image-only pages require reviewed OCR, rather than silently discarding legal text."""
    import pdfplumber

    (tmp_path / "bns.pdf").write_bytes(b"test-only-placeholder")
    pdf = Mock()
    pdf.__enter__ = Mock(return_value=pdf)
    pdf.__exit__ = Mock(return_value=False)
    page = Mock()
    page.extract_text.return_value = "Section text"
    pdf.pages = [page]
    monkeypatch.setattr(pdfplumber, "open", Mock(return_value=pdf))
    assert source_text(tmp_path, "bns") == "Section text"
    page.extract_text.return_value = None
    with pytest.raises(ValueError, match="without text"):
        source_text(tmp_path, "bns")


def test_check_only_parses_without_clients(monkeypatch: pytest.MonkeyPatch) -> None:
    """Source validation can run while containers and model downloads are unavailable."""
    factory = Mock(side_effect=AssertionError("No store startup"))
    monkeypatch.setattr("db.neo4j_store.Neo4jStore", factory)
    monkeypatch.setattr("sys.argv", ["ingest", "--check-only", "--data-dir", str(FIXTURES)])
    main()
    factory.assert_not_called()


def test_missing_source_fails_before_client_startup(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Partial local corpora must not start an incomplete database load."""
    factory = Mock(side_effect=AssertionError("No store startup"))
    monkeypatch.setattr("db.neo4j_store.Neo4jStore", factory)
    monkeypatch.setattr("sys.argv", ["ingest", "--data-dir", str(tmp_path)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    factory.assert_not_called()


def test_ingestion_closes_clients_after_upstream_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed write exits unsuccessfully and still releases both clients."""
    embedder, vectors, graph = clients()
    vectors.upsert_points.side_effect = RuntimeError("sensitive upstream detail")
    monkeypatch.setattr("db.embedder.LegalEmbedder", Mock(return_value=embedder))
    monkeypatch.setattr("db.vector_store.QdrantStore", Mock(return_value=vectors))
    monkeypatch.setattr("db.neo4j_store.Neo4jStore", Mock(return_value=graph))
    monkeypatch.setattr("sys.argv", ["ingest", "--data-dir", str(FIXTURES)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    graph.close.assert_called_once_with()
    vectors.client.close.assert_called_once_with()
