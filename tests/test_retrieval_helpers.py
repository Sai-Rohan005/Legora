"""Exercise real ID, deduplication, query-building, filter, and reranking logic."""

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from retrieval.hybrid_retrieval import HybridRetriever
from retrieval.cross_encoder import LegalReranker


def point(identifier: str | None, score: float = 1.0) -> SimpleNamespace:
    """Create a vector result without requiring a database client or model."""
    return SimpleNamespace(payload={"chunk_id": identifier}, score=score)


@pytest.fixture
def retriever() -> HybridRetriever:
    """Skip expensive initialization; the tested helpers require no services."""
    return HybridRetriever.__new__(HybridRetriever)


@pytest.mark.parametrize("identifier,root", [
    ("BSA-115(2)(a)", "BSA-115"), ("BNSS-45-EXPL-1", "BNSS-45"),
    ("BNS-303(2)", "BNS-303"), ("BNS-303-ILL-a", "BNS-303"),
    ("CONST-21(PROVISO-1)", "CONST-21"), ("CONST-21A", "CONST-21A"),
    ("BSA-2-EXP-1", "BSA-2"), ("BNSS-35-EXP-UNNUMBERED", "BNSS-35"),
    ("article_19_clause_1_sub_a", "CONST-19"), ("article_21A", "CONST-21A"),
])
def test_extract_ids_canonical_roots(retriever: HybridRetriever, identifier: str, root: str) -> None:
    """Both current and existing parser chunk formats resolve to graph root IDs."""
    assert retriever.extract_ids([point(identifier)]) == [root]


def test_extract_ids_deduplicates_roots_and_skips_missing(retriever: HybridRetriever) -> None:
    """Distinct chunks from one section cause only one graph expansion."""
    points = [point("BNS-303(1)"), point("BNS-303(2)"), point(None), point(""), point("BNSS-45")]
    assert set(retriever.extract_ids(points)) == {"BNS-303", "BNSS-45"}
    assert retriever.extract_ids([]) == []


def test_dedupe_keeps_highest_score_for_each_chunk(retriever: HybridRetriever) -> None:
    """Repeated vector hits retain their best candidate, including negative scores."""
    lower, best, other = point("BNS-303", -0.4), point("BNS-303", 0.8), point("BSA-2", -0.1)
    results = retriever.dedupe_points([lower, other, best, point("BNS-303", 0.3)])
    assert results == [best, other]


def test_dedupe_ties_keep_first_and_different_subclauses_survive(retriever: HybridRetriever) -> None:
    """Equal scores are deterministic; sibling chunk IDs must not collapse."""
    first, sibling = point("BNS-303(1)"), point("BNS-303(2)")
    assert retriever.dedupe_points([first, point("BNS-303(1)"), sibling]) == [first, sibling]


def test_dedupe_skips_missing_chunk_ids(retriever: HybridRetriever) -> None:
    """Missing metadata cannot produce an unidentified retained result."""
    assert retriever.dedupe_points([point(None), point("")]) == []
    assert retriever.dedupe_points([]) == []


def test_build_queries_includes_offence_variants_and_unique_concepts(retriever: HybridRetriever) -> None:
    """Offence expansion preserves priority and deduplicates normalized concepts."""
    analysis = SimpleNamespace(offence="Theft", legal_concepts=[" Theft ", "ownership", " OWNERSHIP "])
    assert retriever.build_retrieval_queries(analysis) == [
        "theft", "theft punishment", "theft offence", "whoever commits theft",
        "theft shall be punished", "ownership",
    ]


@pytest.mark.parametrize("concepts,expected", [([], []), (["Article 21", " article 21 "], ["article 21"]), (["", "   ", " Bail "], ["bail"])])
def test_build_queries_without_offence(retriever: HybridRetriever, concepts: list[str], expected: list[str]) -> None:
    """A query without an offence uses only nonempty legal concepts."""
    assert retriever.build_retrieval_queries(SimpleNamespace(offence=None, legal_concepts=concepts)) == expected


@pytest.mark.parametrize("acts,expected", [
    (["BNS"], "bns"), (["BNSS"], "bnss"), (["BSA"], "bsa"),
    (["Constitution"], "constitution"), ([" BnS "], "bns"),
    ([], None), (["IPC"], None), (["IPC", "BNS"], None), (["BSA", "BNS"], "bsa"),
])
def test_document_filter_uses_primary_act(retriever: HybridRetriever, acts: list[str], expected: str | None) -> None:
    """Act matching is case-insensitive and an unsupported primary act stays unfiltered."""
    assert retriever.get_document_filter(SimpleNamespace(acts=acts)) == expected


@pytest.fixture
def reranker() -> LegalReranker:
    """Create the scoring wrapper without downloading or loading a cross encoder."""
    return LegalReranker.__new__(LegalReranker)


@pytest.mark.parametrize("intent,offence,text,expected", [
    ("punishment", None, "The offender shall be punished.", 0.25),
    ("punishment", None, "Punishment is prescribed.", 0.10),
    ("punishment", None, "Imprisonment may follow.", 0.05),
    ("punishment", "theft", "THEFT: shall be punished; punishment includes imprisonment.", 0.55),
    ("punishment", None, "No relevant terms.", 0.0),
    ("evidence", None, "EVIDENCE is admissible.", 0.15),
    ("evidence", "theft", "Evidence of theft.", 0.30),
    ("evidence", None, "Shall be punished with imprisonment.", 0.0),
    ("procedure", None, "PROCEDURE for arrest.", 0.15),
    ("procedure", "arrest", "Procedure for arrest.", 0.30),
    ("procedure", None, "Evidence is admissible.", 0.0),
    ("rights", "theft", "Theft is alleged.", 0.15),
    ("rights", None, "Punishment and procedure and evidence.", 0.0),
    (None, "theft", "Property is missing.", 0.0),
])
def test_legal_boost_by_intent(reranker: LegalReranker, intent: str | None, offence: str | None, text: str, expected: float) -> None:
    """Each intent boosts only its own terms, with an independent offence bonus."""
    analysis = SimpleNamespace(intent=intent, offence=offence)
    assert reranker.legal_boost(-0.2, text, analysis) == pytest.approx(-0.2 + expected)


def test_legal_boost_without_analysis_preserves_score(reranker: LegalReranker) -> None:
    """No analysis means no guessed intent boost."""
    assert reranker.legal_boost(0.4, "shall be punished with imprisonment") == 0.4


def test_rerank_applies_boost_before_truncation(reranker: LegalReranker) -> None:
    """A legally relevant result can outrank a higher raw model score."""
    generic = SimpleNamespace(payload={"chunk_id": "BNS-1", "text": "Unrelated text"})
    relevant = SimpleNamespace(payload={"chunk_id": "BNS-303", "text": "Theft shall be punished with imprisonment"})
    reranker.model = Mock()
    reranker.model.predict.return_value = [0.5, 0.3]
    result = reranker.rerank("theft", [generic, relevant], top_k=1, analysis=SimpleNamespace(offence="theft", intent="punishment"))
    assert result == [relevant]
    assert len(reranker.model.predict.call_args.args[0]) == 2


def test_rerank_uses_enriched_text_and_preserves_tie_order(reranker: LegalReranker) -> None:
    """Enriched passages reach the model and ties remain in input order."""
    first = SimpleNamespace(payload={"text": "plain", "enriched_text": "Statute and section context"})
    second = SimpleNamespace(payload={"text": "fallback"})
    reranker.model = Mock()
    reranker.model.predict.return_value = [0.2, 0.2]
    assert reranker.rerank("question", [first, second]) == [first, second]
    assert reranker.model.predict.call_args.args[0] == [("question", "Statute and section context"), ("question", "fallback")]


def test_empty_rerank_skips_inference(reranker: LegalReranker) -> None:
    """Empty retrieval must not trigger model inference."""
    reranker.model = Mock()
    assert reranker.rerank("question", []) == []
    reranker.model.predict.assert_not_called()
