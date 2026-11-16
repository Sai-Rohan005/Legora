"""Offline ablation tests: real metric/ranking/feature/cache logic, fake service boundaries."""

import csv
import io
import json
import math
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from contextlib import contextmanager

import pytest

from LegalRag.query_analyser import LegalQueryAnalysis
from eval.models import GoldItem
from eval.run_retrieval_eval import (
    CONFIGURATIONS, AnalysisCache, aggregate, bootstrap_mean, csv_report, eligible_gold,
    evaluate, graph_node_ids, live_retriever, main, markdown_table, ranking_metrics,
    run_configuration, seed_everything, worst_failures, write_reports,
)
from eval.storage import write_jsonl
from legora.config import EvaluationSettings
from retrieval.cross_encoder import LegalReranker
from retrieval.hybrid_retrieval import HybridRetriever


def item(ids: list[str] | None = None, **changes: object) -> GoldItem:
    """Use temporary synthetic gold labels, never approve real dataset rows."""
    expected = ids or ["BNS-303"]
    return GoldItem.model_validate({
        "id": "one", "question": "My bike was stolen; what happens next?",
        "act": "MULTI" if len(expected) > 1 else "BNS", "intent": "punishment",
        "expected_chunk_ids": expected, "answerable": True, "reviewed": True, **changes,
    })


def analysis() -> LegalQueryAnalysis:
    """Represent a cached query-only analysis, independent of gold act/support labels."""
    return LegalQueryAnalysis(query_type="criminal", intent="punishment", offence="theft", legal_concepts=["ownership"], entities=[], acts=["BNS"], search_queries=[])


def point(identifier: str, score: float, text: str = "unrelated") -> SimpleNamespace:
    """Make an SDK-shaped dense hit without connecting to a vector store."""
    return SimpleNamespace(payload={"chunk_id": identifier, "text": text}, score=score)


@pytest.fixture
def cache(tmp_path: Path) -> AnalysisCache:
    """Replace the Gemini boundary while running the actual disk cache."""
    return AnalysisCache(tmp_path / "cache", "test-model", 42, Mock(return_value=analysis()))


@pytest.fixture
def retriever() -> HybridRetriever:
    """Run production helpers/reranking with mocked vector, neural, and graph I/O."""
    value = HybridRetriever.__new__(HybridRetriever)
    value.vector_search_filtered = Mock(return_value=[
        point("BNS-1", 0.9), point("BNS-303", 0.8, "Theft shall be punished with imprisonment"),
    ])
    value.reranker = LegalReranker.__new__(LegalReranker)
    value.reranker.model = Mock()
    value.reranker.model.predict.return_value = [0.8, 0.6]
    value.graph = Mock()
    value.graph.run_query.return_value = []
    return value


@pytest.mark.parametrize("match", ("exact", "root"))
def test_perfect_single_rank_metrics(match: str) -> None:
    """A target at rank one has unit recall, reciprocal rank, and nDCG."""
    scores = ranking_metrics(item(), ["BNS-303", "BNS-1"], match)
    assert [scores[name] for name in ("recall_at_1", "recall_at_5", "recall_at_10", "mrr", "ndcg_at_10")] == [1] * 5
    assert scores["context_recall"] is None


def test_multi_target_recall_and_ndcg_use_all_required_sources() -> None:
    """Recall is a target fraction rather than an any-hit success rate."""
    scores = ranking_metrics(item(["BNS-303", "BNS-304"]), ["BNS-1", "BNS-303"], "exact")
    assert scores["recall_at_1"] == 0
    assert scores["recall_at_5"] == 0.5
    assert scores["recall_at_10"] == 0.5
    assert scores["mrr"] == 0.5
    assert scores["ndcg_at_10"] == pytest.approx((1 / math.log2(3)) / (1 + 1 / math.log2(3)))


def test_mrr_uses_full_candidate_depth_while_ndcg_stops_at_ten() -> None:
    """A rank-11 target contributes to MRR but not Recall@10 or nDCG@10."""
    scores = ranking_metrics(item(), [f"BNS-{index}" for index in range(1, 11)] + ["BNS-303"], "exact")
    assert scores["mrr"] == pytest.approx(1 / 11)
    assert scores["recall_at_10"] == scores["ndcg_at_10"] == 0


def test_root_matching_collapses_target_identity_without_compacting_ranks() -> None:
    """Repeated root hits occupy rank positions and receive relevance credit only once."""
    gold = item(["BNS-303(1)", "BNS-303(2)", "BSA-115(2)(a)"])
    ranked = ["BNS-303(1)"] * 5 + ["BSA-115-EXP-1"]
    scores = ranking_metrics(gold, ranked, "root")
    assert scores["recall_at_1"] == scores["recall_at_5"] == 0.5
    assert scores["recall_at_10"] == 1
    assert scores["ndcg_at_10"] == pytest.approx((1 + 1 / math.log2(7)) / (1 + 1 / math.log2(3)))
    assert ranking_metrics(gold, ranked, "exact")["recall_at_10"] == pytest.approx(1 / 3)


def test_legacy_constitution_ids_match_only_on_root() -> None:
    """Root scoring maps both stored legacy IDs and graph IDs to one article."""
    gold = item(["article_21_clause_1"], act="Constitution")
    assert ranking_metrics(gold, ["CONST-21(2)"], "root")["recall_at_1"] == 1
    assert ranking_metrics(gold, ["CONST-21(2)"], "exact")["recall_at_1"] == 0


def test_single_alternates_receive_one_relevance_credit() -> None:
    """Multiple interchangeable hits cannot make recall or nDCG exceed one."""
    gold = item(acceptable_alternates=["BNS-303(2)"])
    scores = ranking_metrics(gold, ["BNS-303(2)", "BNS-303"], "exact")
    assert scores["ndcg_at_10"] == scores["recall_at_10"] == 1


def test_flat_alternates_do_not_replace_a_multi_target_set() -> None:
    """Unmapped multi-source alternates must not fabricate complete target coverage."""
    gold = item(["BNS-303", "BSA-2"], acceptable_alternates=["BSA-3"])
    assert ranking_metrics(gold, ["BNS-303", "BSA-3"], "exact")["recall_at_10"] == 0.5


def test_empty_retrieval_scores_zero_without_undefined_ndcg() -> None:
    """An actual empty result is a measured failure, not a missing category."""
    scores = ranking_metrics(item(), [], "exact", [])
    assert all(value == 0 for value in scores.values())


def test_graph_context_and_combined_context_are_distinct() -> None:
    """Report graph-only coverage separately from the union with retrieved passages."""
    gold = item(["BNS-303", "BSA-2"])
    scores = ranking_metrics(gold, ["BNS-303"], "exact", ["BSA-2"])
    assert scores["context_recall"] == 0.5
    assert scores["combined_context_recall"] == 1


def test_graph_extractor_ignores_labels_and_textual_cross_references() -> None:
    """A requested graph root or an ID mentioned in prose is not a returned node."""
    value = {"BNS-303": {"children": [{"p": [{"id": "BSA-2"}, "BELONGS_TO", {"id": "BNS-1"}]}], "text": "see BNS-303", "references": []}}
    assert graph_node_ids(value) == {"BSA-2", "BNS-1"}
    assert graph_node_ids(SimpleNamespace(nodes=[{"id": "CONST-21"}])) == {"CONST-21"}


def test_a_is_original_unfiltered_dense_without_analysis(retriever: HybridRetriever, cache: AnalysisCache) -> None:
    """The baseline must not use Gemini, gold act metadata, expansion, or reranking."""
    outcome = run_configuration("Original question", CONFIGURATIONS["A"], retriever, cache, 10)
    retriever.vector_search_filtered.assert_called_once_with("Original question", document=None, k=10)
    cache.analyse.assert_not_called()
    retriever.reranker.model.predict.assert_not_called()
    retriever.graph.run_query.assert_not_called()
    assert outcome["ranked_ids"] == ["BNS-1", "BNS-303"]
    assert outcome["graph_ids"] is None


def test_b_uses_analysis_filter_and_preserves_original_query(retriever: HybridRetriever, cache: AnalysisCache) -> None:
    """The filter comes from cached analysis while the retrieval query stays original."""
    run_configuration("Original question", CONFIGURATIONS["B"], retriever, cache, 10)
    retriever.vector_search_filtered.assert_called_once_with("Original question", document="bns", k=10)
    cache.analyse.assert_called_once_with("Original question")


def test_c_adds_expansion_and_caps_merged_candidate_budget(retriever: HybridRetriever, cache: AnalysisCache) -> None:
    """Expansion includes B's original query and shares the same merged top-N budget."""
    retriever.vector_search_filtered.return_value = [point(f"BNS-{index}", 1 - index / 100) for index in range(20)]
    result = run_configuration("Original question", CONFIGURATIONS["C"], retriever, cache, 10)
    queries = [entry.args[0] for entry in retriever.vector_search_filtered.call_args_list]
    assert queries == ["Original question", *retriever.build_retrieval_queries(analysis())]
    assert result["candidate_count"] == 10
    assert result["ranked_ids"] == [f"BNS-{index}" for index in range(10)]


def test_d_and_e_differ_only_by_legal_boost(retriever: HybridRetriever, cache: AnalysisCache) -> None:
    """The same raw neural scores flip order only when production boosts are enabled."""
    d = run_configuration("question", CONFIGURATIONS["D"], retriever, cache, 10)
    e = run_configuration("question", CONFIGURATIONS["E"], retriever, cache, 10)
    assert d["ranked_ids"] == ["BNS-1", "BNS-303"]
    assert e["ranked_ids"] == ["BNS-303", "BNS-1"]
    first, second = retriever.reranker.model.predict.call_args_list
    assert first == second
    cache.analyse.assert_called_once()


def test_f_preserves_e_ranking_and_collects_actual_graph_ids(retriever: HybridRetriever, cache: AnalysisCache) -> None:
    """Graph expansion improves available context without being treated as a ranked hit."""
    retriever.graph.run_query.return_value = [{"ref": {"id": "BSA-2"}}]
    e = run_configuration("question", CONFIGURATIONS["E"], retriever, cache, 10)
    f = run_configuration("question", CONFIGURATIONS["F"], retriever, cache, 10)
    assert e["ranked_ids"] == f["ranked_ids"]
    assert f["graph_ids"] == ["BSA-2"]
    assert ranking_metrics(item(["BSA-2"], act="BSA"), f["ranked_ids"], "exact", f["graph_ids"])["context_recall"] == 1


def test_dense_ties_have_stable_chunk_id_order(retriever: HybridRetriever, cache: AnalysisCache) -> None:
    """Backend tie ordering cannot arbitrarily alter the benchmark ranking."""
    retriever.vector_search_filtered.return_value = [point("BNS-2", 1), point("BNS-1", 1)]
    assert run_configuration("question", CONFIGURATIONS["A"], retriever, cache, 10)["ranked_ids"] == ["BNS-1", "BNS-2"]


def test_analysis_disk_cache_reuses_exact_inputs_and_invalidates_model_or_seed(tmp_path: Path) -> None:
    """A fresh process can reproduce an earlier analysis with no Gemini call."""
    function = Mock(return_value=analysis())
    first = AnalysisCache(tmp_path, "model", 42, function)
    assert first.get("question") == analysis()
    forbidden = Mock(side_effect=AssertionError("No LLM call expected"))
    assert AnalysisCache(tmp_path, "model", 42, forbidden, offline=True).get("question") == analysis()
    forbidden.assert_not_called()
    for model, seed in (("different", 42), ("model", 43)):
        with pytest.raises(ValueError, match="cache miss"):
            AnalysisCache(tmp_path, model, seed, forbidden, offline=True).get("question")
    function.assert_called_once_with("question")


def test_analysis_refresh_and_corruption_are_explicit(tmp_path: Path) -> None:
    """Do not silently replace corrupted cache data with another nondeterministic analysis."""
    function = Mock(return_value=analysis())
    AnalysisCache(tmp_path, "model", 42, function).get("question")
    AnalysisCache(tmp_path, "model", 42, function, refresh=True).get("question")
    assert function.call_count == 2
    path = next(tmp_path.glob("*.json"))
    path.write_text("not JSON")
    with pytest.raises(ValueError):
        AnalysisCache(tmp_path, "model", 42, function).get("question")
    assert function.call_count == 2


def test_analyser_signature_changes_cache_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Prompt or schema revisions must not reuse analyses generated by old code."""
    AnalysisCache(tmp_path, "model", 42, Mock(return_value=analysis())).get("question")
    monkeypatch.setattr("eval.run_retrieval_eval.analysis_signature", lambda: "new-signature")
    with pytest.raises(ValueError, match="cache miss"):
        AnalysisCache(tmp_path, "model", 42, Mock(), offline=True).get("question")


def test_bootstrap_intervals_are_seeded_and_degenerate_for_singletons() -> None:
    """Intervals are empirical query resamples, including the one-query edge case."""
    assert bootstrap_mean([0, 0.5, 1], 42, 1000) == bootstrap_mean([0, 0.5, 1], 42, 1000)
    assert bootstrap_mean([0.25], 42, 1000) == (0.25, 0.25, 0.25)
    mean, low, high = bootstrap_mean([0, 1], 42, 1000)
    assert mean == 0.5 and 0 <= low <= high <= 1


def test_evaluation_gates_drafts_and_refusals_and_aggregates_by_intent(tmp_path: Path, retriever: HybridRetriever, cache: AnalysisCache) -> None:
    """Only approved answerable questions affect numerators, denominators, or service calls."""
    included = [item(id="punishment"), item(id="rights", intent="rights")]
    ignored = [item(id="draft", reviewed=False), item(id="refusal", answerable=False, expected_chunk_ids=[], act="OUT_OF_SCOPE", intent="out_of_scope")]
    path = tmp_path / "gold.jsonl"
    write_jsonl(path, included + ignored)
    assert [entry.id for entry in eligible_gold(path)] == ["punishment", "rights"]
    rows, details = evaluate(included + ignored, [CONFIGURATIONS["A"]], retriever, cache, 10)
    assert len(rows) == 4 and len(details) == 2
    summaries = aggregate(rows, 42, 100)
    assert all(row["n"] == 2 for row in summaries)
    intents = aggregate(rows, 42, 100, by_intent=True)
    assert {row["intent"] for row in intents} == {"punishment", "rights"}
    assert all(row["n"] == 1 for row in intents)
    assert retriever.vector_search_filtered.call_count == 2


def test_report_files_include_cis_and_ranked_failure_details(tmp_path: Path, retriever: HybridRetriever, cache: AnalysisCache) -> None:
    """A synthetic completed run exercises CSV, markdown, intent, and worst-case artifacts."""
    rows, details = evaluate([item(["BNS-999"])], [CONFIGURATIONS["A"]], retriever, cache, 10)
    summaries = aggregate(rows, 42, 100)
    failures = worst_failures(rows, details)
    assert failures[0]["expected_chunk_ids"] == ["BNS-999"]
    assert failures[0]["ranked_ids"] == ["BNS-1", "BNS-303"]
    report = write_reports(tmp_path, summaries, aggregate(rows, 42, 100, True), failures, details, {"status": "completed"})
    parsed = list(csv.DictReader(io.StringIO((tmp_path / "retrieval_ablation.csv").read_text())))
    assert len(parsed) == 2
    assert parsed[0]["recall_at_10_ci_low"] == "0.0"
    assert "BNS-999" in report and "BNS-303" in report
    assert "Worst 10" in report and "Per-intent" in report
    assert "[0.000, 0.000]" in markdown_table(summaries)
    assert json.loads((tmp_path / "retrieval_ablation_worst10.json").read_text()) == failures


def test_empty_gold_stops_before_live_clients_and_writes_no_scores(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The real current corpus/gold blockers must not produce invented ablation values."""
    path, directory = tmp_path / "gold.jsonl", tmp_path / "results"
    write_jsonl(path, [item(reviewed=False)])
    live = Mock(side_effect=AssertionError("No model or database startup expected"))
    monkeypatch.setattr("eval.run_retrieval_eval.live_retriever", live)
    monkeypatch.setattr("sys.argv", ["eval", "--gold", str(path), "--output-dir", str(directory)])
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert list(csv.DictReader(io.StringIO((directory / "retrieval_ablation.csv").read_text()))) == []
    assert "not run" in (directory / "retrieval_ablation.md").read_text()
    live.assert_not_called()


def test_a_loads_no_neural_reranker_or_graph(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A needs only Qdrant and the embedding model, with exact dense search by default."""
    vector, embedder, reranker, graph = Mock(), Mock(), Mock(), Mock()
    monkeypatch.setattr("db.vector_store.QdrantStore", vector)
    monkeypatch.setattr("db.embedder.LegalEmbedder", embedder)
    monkeypatch.setattr("db.neo4j_store.Neo4jStore", graph)
    monkeypatch.setattr("retrieval.cross_encoder.LegalReranker", reranker)
    settings = EvaluationSettings(_env_file=None, gemini_api_key=None, qdrant_url="http://example.invalid")
    with live_retriever([CONFIGURATIONS["A"]], settings, "legal_rag", "embedding", "reranking"):
        pass
    assert vector.call_args.kwargs["exact_search"] is True
    vector.return_value.client.close.assert_called_once()
    embedder.assert_called_once_with(model_name="embedding")
    reranker.assert_not_called()
    graph.assert_not_called()


def test_seeded_local_random_generators_repeat() -> None:
    """The runner seeds the actual local RNGs used by embedding/reranking libraries."""
    import random
    import numpy as np
    import torch

    previous = torch.are_deterministic_algorithms_enabled()
    try:
        seed_everything(42)
        first = (random.random(), np.random.rand(), torch.rand(1).item())
        seed_everything(42)
        assert first == (random.random(), np.random.rand(), torch.rand(1).item())
    finally:
        torch.use_deterministic_algorithms(previous)


def test_cli_overrides_and_cached_analysis_produce_complete_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, retriever: HybridRetriever,
) -> None:
    """A completed CLI run can use an analysis cache with no Gemini credentials."""
    gold, directory, cache_dir = tmp_path / "gold.jsonl", tmp_path / "results", tmp_path / "cache"
    write_jsonl(gold, [item()])
    AnalysisCache(cache_dir, "test-model", 42, Mock(return_value=analysis())).get(item().question)
    retriever.embedder = SimpleNamespace(model=[SimpleNamespace(auto_model=SimpleNamespace(config=SimpleNamespace(_commit_hash="test-revision")))])

    @contextmanager
    def live(*args: object, **kwargs: object):
        """Replace only the model/database construction boundary."""
        yield retriever

    forbidden = Mock(side_effect=AssertionError("Cached run must not create a Gemini client"))
    settings = EvaluationSettings(_env_file=None, gemini_api_key=None, gemini_model="test-model")
    monkeypatch.setattr("eval.run_retrieval_eval.EvaluationSettings", lambda: settings)
    monkeypatch.setattr("eval.run_retrieval_eval.live_retriever", live)
    monkeypatch.setattr("eval.run_retrieval_eval.Analyser", forbidden)
    monkeypatch.setattr("sys.argv", [
        "eval", "--gold", str(gold), "--output-dir", str(directory), "--configs", "A",
        "--act-filter", "--offline-analysis", "--analysis-cache", str(cache_dir), "--bootstrap-samples", "100",
    ])
    main()
    forbidden.assert_not_called()
    assert retriever.vector_search_filtered.call_args.kwargs["document"] == "bns"
    metadata = json.loads((directory / "retrieval_ablation_run.json").read_text())
    assert metadata["configurations"][0]["act_filter"] is True
    assert metadata["analysis_cache_misses"] == 0
    assert metadata["model_revisions"]["embedder"] == "test-revision"
    rows = list(csv.DictReader(io.StringIO((directory / "retrieval_ablation.csv").read_text())))
    assert len(rows) == 2 and float(rows[0]["recall_at_5"]) == 1


def test_qdrant_exact_search_is_opt_in_for_production(monkeypatch: pytest.MonkeyPatch) -> None:
    """The evaluation switch sends exact search parameters without changing production defaults."""
    from db.vector_store import QdrantStore

    monkeypatch.setattr("db.vector_store.QdrantClient", Mock())
    settings = EvaluationSettings(_env_file=None, qdrant_url="http://example.invalid")
    for exact in (True, False):
        store = QdrantStore(settings=settings, exact_search=exact)
        store.search_with_filter([1.0], document="bns")
        kwargs = store.client.query_points.call_args.kwargs
        if exact:
            assert kwargs["search_params"].exact is True
        else:
            assert "search_params" not in kwargs


def test_worst_failures_are_capped_and_include_poor_ranking_with_full_recall(
    retriever: HybridRetriever, cache: AnalysisCache,
) -> None:
    """A target at rank two is still a useful failure; severe misses come first."""
    questions = [item(["BNS-999"], id=f"miss-{index:02d}") for index in range(12)] + [item(id="rank-two")]
    rows, details = evaluate(questions, [CONFIGURATIONS["A"]], retriever, cache, 10)
    assert len(worst_failures(rows, details)) == 10
    all_failures = worst_failures(rows, details, limit=20)
    assert [row["id"] for row in all_failures[:2]] == ["miss-00", "miss-01"]
    assert all_failures[-1]["id"] == "rank-two"
    assert all_failures[-1]["root_recall_at_10"] == 1
    assert all_failures[-1]["root_ndcg_at_10"] < 1


def test_g_uses_shared_bm25_fusion_before_real_reranking(
    retriever: HybridRetriever, cache: AnalysisCache,
) -> None:
    """Sparse retrieval recovers a dense miss through the same helper used at runtime."""
    from threading import Lock
    from retrieval.lexical import BM25Retriever, RetrievalHit

    sparse_hit = RetrievalHit(payload={"chunk_id": "BNS-999", "text": "ownership"})
    retriever._bm25 = BM25Retriever([*retriever.vector_search_filtered.return_value, sparse_hit])
    retriever._bm25_lock = Lock()
    retriever.reranker.model.predict.side_effect = lambda pairs, **kwargs: [0.9 if "ownership" in passage else 0.1 for _, passage in pairs]
    e = run_configuration("ownership question", CONFIGURATIONS["E"], retriever, cache, 10)
    g = run_configuration("ownership question", CONFIGURATIONS["G"], retriever, cache, 10)
    assert "BNS-999" not in e["ranked_ids"]
    assert g["ranked_ids"][0] == "BNS-999"
    assert len(g["ranked_ids"]) <= 10
    assert g["graph_ids"] is None
    gold = item(["BNS-999"], question="ownership question")
    rows, _ = evaluate([gold], [CONFIGURATIONS["E"], CONFIGURATIONS["G"]], retriever, cache, 10)
    summaries = aggregate(rows, 42, 100)
    by_config = {row["configuration"]: row for row in summaries if row["match"] == "root"}
    assert by_config["E"]["recall_at_5"] == 0
    assert by_config["G"]["recall_at_5"] == 1
    assert "G" in markdown_table(summaries)


def test_g_exact_lookup_is_pinned_after_reranking(retriever: HybridRetriever, cache: AnalysisCache) -> None:
    """The evaluation route retains the explicitly requested stored result at rank one."""
    from dataclasses import replace

    exact = point("BNS-303", 0.0)
    retriever.vector_db = Mock()
    retriever.vector_db.lookup_chunk_ids.return_value = [exact]
    retriever.reranker.model.predict.return_value = [100, -100]
    outcome = run_configuration("section 303 BNS", replace(CONFIGURATIONS["G"], bm25=False), retriever, cache, 10)
    assert outcome["ranked_ids"][0] == "BNS-303"
    assert outcome["exact_lookup_ids"] == ["BNS-303"]
