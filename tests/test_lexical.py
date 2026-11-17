"""Real BM25/RRF/routing tests with database and neural boundaries mocked."""

from threading import Lock
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from db.vector_store import QdrantStore
from legora.config import Settings
from retrieval.hybrid_retrieval import HybridRetriever
from retrieval.lexical import BM25Retriever, RetrievalHit, explicit_provisions, prepend_exact, reciprocal_rank_fusion, tokenize


def hit(identifier: str, text: str = "text", score: float = 1.0, **payload: object) -> RetrievalHit:
    """Create an actual lexical hit with an exact stored chunk ID."""
    return RetrievalHit(payload={"chunk_id": identifier, "text": text, **payload}, score=score)


@pytest.fixture
def index() -> BM25Retriever:
    """Index a small corpus with genuine BM25 scores, not mocked score outputs."""
    return BM25Retriever([
        hit("BNS-303", "theft stolen bicycle", document="bns"),
        hit("BSA-2", "evidence witness proof", document="bsa"),
        hit("BNSS-35", "arrest procedure warrant", document="bnss"),
        hit("article_21", "rights liberty equality"),
        hit("BNS-304", "property theft", document="bns"),
    ])


def test_bm25_retrieves_lexical_matches(index: BM25Retriever) -> None:
    """Specific terms recover a provision independently of dense similarity."""
    assert [point.payload["chunk_id"] for point in index.search("My bicycle was stolen")] == ["BNS-303"]
    assert index.search("STOLEN bicycle")[0].score > 0


def test_bm25_act_filter_and_legacy_metadata(index: BM25Retriever) -> None:
    """Use the same act restriction while supporting stored legacy Constitution IDs."""
    assert index.search("theft", document="bsa") == []
    assert index.search("liberty", document="constitution")[0].payload["chunk_id"] == "article_21"
    assert len(index.search("theft", document="bns", k=1)) == 1


def test_bm25_ignores_zero_overlap_instead_of_padding(index: BM25Retriever) -> None:
    """No-overlap passages must not acquire RRF rank credit."""
    assert index.search("nonexistentword") == []
    assert index.search("!!!") == []
    assert index.search("theft", k=0) == []
    assert BM25Retriever([]).search("theft") == []


def test_single_document_negative_bm25_scores_are_still_matches() -> None:
    """BM25Okapi can return negative IDF scores; positivity is not a relevance test."""
    index = BM25Retriever([hit("BNS-303", "theft")])
    assert index.search("theft")[0].payload["chunk_id"] == "BNS-303"


def test_bm25_uses_enriched_text_and_rejects_conflicting_duplicates() -> None:
    """The index retains one stored payload per ID and includes source headings."""
    source = hit("BNS-303", "plain", enriched_text="Theft punishment")
    assert len(BM25Retriever([source, source]).hits) == 1
    assert BM25Retriever([source]).search("punishment")
    with pytest.raises(ValueError, match="Conflicting"):
        BM25Retriever([source, hit("BNS-303", "different")])


def test_tokenizer_preserves_unicode_words_and_section_numbers() -> None:
    """Case/punctuation normalization keeps lexical numbers and multilingual tokens."""
    assert tokenize("Section 303—THEFT, café") == ["section", "303", "theft", "café"]


def test_rrf_k60_formula_and_shared_candidate_priority() -> None:
    """Ranks, not incomparable raw dense/BM25 scores, determine fusion."""
    a, b, c = hit("BNS-1", score=1000), hit("BNS-2", score=0.1), hit("BNS-3", score=100000)
    fused = reciprocal_rank_fusion([[a, b], [b, c]])
    assert [point.payload["chunk_id"] for point in fused] == ["BNS-2", "BNS-1", "BNS-3"]
    assert fused[0].score == pytest.approx(1 / 62 + 1 / 61)
    assert a.score == 1000


def test_rrf_duplicate_credit_ties_and_budget() -> None:
    """Duplicate entries get one contribution per stream and ties have stable IDs."""
    a, b = hit("BNS-1"), hit("BNS-2")
    fused = reciprocal_rank_fusion([[a, a], [b]], limit=1)
    assert len(fused) == 1 and fused[0].payload["chunk_id"] == "BNS-1"
    assert fused[0].score == pytest.approx(1 / 61)
    assert reciprocal_rank_fusion([[], []]) == []
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([[a]], k=0)


@pytest.mark.parametrize("query,expected", [
    ("What is the punishment under section 303 BNS?", [["BNS-303"]]),
    ("BNS section 303", [["BNS-303"]]),
    ("section 35 of the BNSS", [["BNSS-35"]]),
    ("Section 115(2)(a) BSA", [["BSA-115(2)(a)"]]),
    ("section 35(2A)(b) BNSS", [["BNSS-35(2A)(b)"]]),
    ("section 303 Bharatiya Nyaya Sanhita", [["BNS-303"]]),
    ("Constitution article 21", [["CONST-21", "article_21"]]),
    ("article 19(1)(a) of the Constitution", [["CONST-19(1)(a)", "article_19_clause_1_sub_a"]]),
    ("section 303 BNS and section 35 BNSS", [["BNS-303"], ["BNSS-35"]]),
    ("Under BNS, explain section 303", [["BNS-303"]]),
    ("section 303", []), ("303 years ago", []),
    ("BNS and BNSS; what is section 303?", []),
])
def test_explicit_provision_routing(query: str, expected: list[list[str]]) -> None:
    """Require an explicit act, preserve qualification, and never infer from gold labels."""
    assert explicit_provisions(query) == expected


def test_exact_lookup_uses_stored_ids_and_legacy_fallback() -> None:
    """A canonical graph ID can resolve to an existing legacy stored Constitution chunk."""
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.vector_db = Mock()
    source = hit("article_21", "liberty")
    retriever.vector_db.lookup_chunk_ids.return_value = [source]
    assert retriever.exact_matches("article 21 Constitution") == [source]
    retriever.vector_db.lookup_chunk_ids.assert_called_once_with(["CONST-21", "article_21"])
    retriever.vector_db.lookup_chunk_ids.reset_mock()
    assert retriever.exact_matches("section 303") == []
    retriever.vector_db.lookup_chunk_ids.assert_not_called()


def test_missing_exact_id_is_not_fabricated() -> None:
    """An explicit but nonexistent provision does not become a synthetic hit."""
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.vector_db = Mock()
    retriever.vector_db.lookup_chunk_ids.return_value = []
    assert retriever.exact_matches("section 999 BNS") == []


def test_bm25_snapshot_is_built_once() -> None:
    """Repeated retrieval queries must not rescan the full stored corpus."""
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever._bm25 = None
    retriever._bm25_lock = Lock()
    retriever.vector_db = Mock()
    retriever.vector_db.iter_chunks.return_value = [hit("BNS-303", "theft")]
    assert retriever.get_bm25() is retriever.get_bm25()
    retriever.vector_db.iter_chunks.assert_called_once_with()


def test_fusion_protects_exact_hit_from_candidate_truncation(index: BM25Retriever) -> None:
    """An explicitly requested stored ID is included even if dense retrieval missed it."""
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever._bm25, retriever._bm25_lock = index, Lock()
    retriever.vector_db = Mock()
    exact = hit("BNS-303", "theft stolen bicycle")
    retriever.vector_db.lookup_chunk_ids.return_value = [exact]
    fused, pinned = retriever.fuse_candidates("section 303 BNS", [hit("BNS-1", score=0.9)], "bns", 1, True, True)
    assert fused == pinned == [exact]
    assert prepend_exact([hit("BNS-1"), exact], pinned, 1) == [exact]


def test_runtime_fusion_happens_before_reranking_and_exact_stays_first(index: BM25Retriever) -> None:
    """The real HybridRetriever path keeps explicit routing despite a lower neural score."""
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.use_bm25 = retriever.exact_id_lookup = True
    retriever._bm25, retriever._bm25_lock = index, Lock()
    retriever.vector_db = Mock()
    exact, other = hit("BNS-303", "theft"), hit("BNS-1", "unrelated")
    retriever.vector_db.lookup_chunk_ids.return_value = [exact]
    retriever.analyser = Mock()
    retriever.analyser.analyze_query.return_value = SimpleNamespace(offence="theft", legal_concepts=[], acts=["BNS"])
    retriever.vector_search_filtered = Mock(return_value=[other])
    retriever.reranker = Mock()
    retriever.reranker.rerank.return_value = [other, exact]
    with patch("retrieval.hybrid_retrieval.get_settings", return_value=SimpleNamespace(top_k=10, rerank_k=2)):
        result = retriever.retrieve("section 303 BNS", include_graph=False)
    passed = retriever.reranker.rerank.call_args.kwargs["points"]
    assert passed[0] == exact
    assert result["reranked_results"][0] == exact
    assert result["vector_results"] == [other]
    assert result["fused_results"][0] == exact
    assert len({point.payload["chunk_id"] for point in result["reranked_results"]}) == 2


def test_qdrant_payload_scroll_and_exact_lookup_filters() -> None:
    """Lookup matches payload.chunk_id rather than numeric/UUID Qdrant point IDs."""
    store = QdrantStore.__new__(QdrantStore)
    store.collection_name = "legal_rag"
    store.client = Mock()
    store.client.scroll.side_effect = [
        ([SimpleNamespace(id=7, payload={"chunk_id": "BNS-303", "text": "theft"})], "next"),
        ([], None),
    ]
    assert store.lookup_chunk_ids(["BNS-303"])[0].id == 7
    first, second = store.client.scroll.call_args_list
    assert first.kwargs["scroll_filter"].should[0].key == "chunk_id"
    assert first.kwargs["scroll_filter"].should[0].match.value == "BNS-303"
    assert not first.kwargs["with_vectors"] and second.kwargs["offset"] == "next"
    store.client.scroll.reset_mock()
    assert store.lookup_chunk_ids([]) == []
    store.client.scroll.assert_not_called()


def test_bm25_default_remains_disabled() -> None:
    """Unmeasured sparse retrieval must not silently change the production default."""
    settings = Settings(
        _env_file=None, gemini_api_key="test", qdrant_url="http://test.invalid",
        neo4j_uri="bolt://test.invalid", neo4j_username="test", neo4j_password="test", kanoon_token="test",
    )
    assert settings.use_bm25 is False
    assert settings.exact_id_lookup is None


def test_multiple_exact_hits_do_not_exceed_candidate_budget() -> None:
    """Later pinning must not reintroduce exact hits excluded by the retrieval limit."""
    retriever = HybridRetriever.__new__(HybridRetriever)
    retriever.vector_db = Mock()
    retriever.vector_db.lookup_chunk_ids.return_value = [hit("BNS-303"), hit("BNSS-35")]
    fused, exact = retriever.fuse_candidates("section 303 BNS and section 35 BNSS", [], None, 1, False, True)
    assert len(fused) == len(exact) == 1
    assert fused[0].payload["chunk_id"] == "BNS-303"


def test_startup_indexes_only_when_explicitly_enabled() -> None:
    """Default startup performs no corpus scan; opt-in startup builds a single snapshot."""
    settings = SimpleNamespace(use_bm25=False, exact_id_lookup=None,
                               vector_search_workers=1, batch_graph_expansion=False, enable_query_cache=False)
    with patch("retrieval.hybrid_retrieval.get_settings", return_value=settings), patch(
        "retrieval.hybrid_retrieval.Neo4jStore"
    ), patch("retrieval.hybrid_retrieval.LegalEmbedder"), patch(
        "retrieval.hybrid_retrieval.LegalReranker"
    ), patch("retrieval.hybrid_retrieval.Analyser"), patch("retrieval.hybrid_retrieval.QdrantStore") as store:
        store.return_value.iter_chunks.return_value = [hit("BNS-303", "theft")]
        default = HybridRetriever()
        assert not default.use_bm25 and not default.exact_id_lookup
        store.return_value.iter_chunks.assert_not_called()
        enabled = HybridRetriever(use_bm25=True)
        assert enabled.use_bm25 and enabled.exact_id_lookup
        assert enabled.get_bm25().search("theft")
        store.return_value.iter_chunks.assert_called_once_with()
