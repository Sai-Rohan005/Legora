"""Regression tests using mocked services; no model downloads or API calls."""

import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from LegalRag.rag_pipeline import RAGPipeline
from db.graph_builders.bns_graph_builder import BNSGraphBuilder
from db.neo4j_store import Neo4jStore
from retrieval.hybrid_retrieval import HybridRetriever
from retrieval.usage import LegalRetriever


class RetryTests(unittest.TestCase):
    """Check the budget across failure stages and repeated searches."""

    def make_pipeline(self, budget: int, stage: str) -> RAGPipeline:
        """Construct the real pipeline with external clients mocked."""
        with patch("LegalRag.rag_pipeline.LegalRetriever"), patch(
            "LegalRag.rag_pipeline.LegalLLM"
        ), patch("LegalRag.rag_pipeline.LegalLLMEvaluator"):
            pipeline = RAGPipeline(max_attempts=budget)
        pipeline.retriever.retrieve.return_value = {"final_context": "context"}
        pipeline.llm.generate.return_value = "answer"
        pipeline.evaluator.evaluate.return_value = {
            "overall_score": 20, "failure_stage": stage
        }
        return pipeline

    def test_failure_uses_exact_budget(self) -> None:
        """Every failed search makes exactly max_attempts complete attempts."""
        for budget in (1, 2, 3, 5):
            for stage in ("RETRIEVAL", "RERANKING", "CONTEXT", "GENERATION", "CITATION", "UNKNOWN"):
                with self.subTest(budget=budget, stage=stage):
                    pipeline = self.make_pipeline(budget, stage)
                    with patch.object(pipeline, "adjust_for_retry", wraps=pipeline.adjust_for_retry) as adjust:
                        result = pipeline.search("theft")
                    self.assertEqual(result["status"], "FAIL")
                    self.assertEqual(result["attempts"], budget)
                    self.assertEqual(pipeline.attempt, budget)
                    for method in (pipeline.retriever.retrieve, pipeline.llm.generate, pipeline.evaluator.evaluate):
                        self.assertEqual(method.call_count, budget)
                    self.assertEqual(adjust.call_count, budget - 1)

    def test_success_on_last_attempt(self) -> None:
        """The final allowed attempt can succeed without another adjustment."""
        pipeline = self.make_pipeline(3, "RETRIEVAL")
        pipeline.evaluator.evaluate.side_effect = [
            {"overall_score": 0}, {"overall_score": 0}, {"overall_score": 90}
        ]
        result = pipeline.search("theft")
        self.assertEqual((result["status"], result["attempts"]), ("PASS", 3))

    def test_early_success_and_new_search_reset(self) -> None:
        """Each new search starts with a fresh budget and tuning state."""
        pipeline = self.make_pipeline(3, "RETRIEVAL")
        pipeline.search("theft")
        pipeline.evaluator.evaluate.return_value = {"overall_score": 90}
        result = pipeline.search("Article 21")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(pipeline.retrieval_kwargs, {})
        self.assertEqual(pipeline.generation_kwargs, {})
        self.assertEqual(pipeline.current_query, "Article 21")

    def test_invalid_budget(self) -> None:
        """Reject budgets that cannot produce an answer."""
        for budget in (0, -1):
            with self.assertRaisesRegex(ValueError, "max_attempts"):
                RAGPipeline(budget)

    def test_info_logs_exclude_query(self) -> None:
        """Attempt logging does not expose the user's legal question."""
        pipeline = self.make_pipeline(1, "RETRIEVAL")
        with self.assertLogs("LegalRag.rag_pipeline", level="INFO") as logs:
            pipeline.search("private query marker")
        self.assertNotIn("private query marker", " ".join(logs.output))


class ConfigurationTests(unittest.TestCase):
    """Validate environment-only graph configuration without connecting."""

    def test_missing_configuration_fails_before_driver_creation(self) -> None:
        """Each missing or blank required variable is named without values."""
        config = {"NEO4J_URI": "neo4j://example.invalid", "NEO4J_USERNAME": "example-user", "NEO4J_PASSWORD": "example-secret"}
        for name in config:
            for value in (None, "", "   "):
                env = dict(config)
                if value is None:
                    env.pop(name)
                else:
                    env[name] = value
                with self.subTest(name=name, value=value), patch.dict(os.environ, env, clear=True), patch("db.neo4j_store.GraphDatabase.driver") as driver:
                    with self.assertRaisesRegex(ValueError, name) as error:
                        Neo4jStore()
                    self.assertNotIn("example-secret", str(error.exception))
                    driver.assert_not_called()

    def test_driver_uses_environment(self) -> None:
        """Pass configured values unchanged to the Neo4j driver."""
        with patch.dict(os.environ, {"NEO4J_URI": "neo4j://example.invalid", "NEO4J_USERNAME": "example-user", "NEO4J_PASSWORD": "example-secret"}, clear=True), patch("db.neo4j_store.GraphDatabase.driver") as driver:
            Neo4jStore()
        driver.assert_called_once_with("neo4j://example.invalid", auth=("example-user", "example-secret"))

    def test_hybrid_fails_before_loading_models(self) -> None:
        """A configuration error must not trigger expensive model loading."""
        with patch.dict(os.environ, {}, clear=True), patch("retrieval.hybrid_retrieval.LegalEmbedder") as embedder:
            with self.assertRaisesRegex(ValueError, "NEO4J_URI"):
                HybridRetriever()
        embedder.assert_not_called()


class GraphTests(unittest.TestCase):
    """Check hierarchy direction through the builder and query boundaries."""

    def test_queries_follow_opposite_directions(self) -> None:
        """Children follow incoming BELONGS_TO edges; ancestors outgoing."""
        retriever = HybridRetriever.__new__(HybridRetriever)
        retriever.graph = Mock()
        retriever.get_children("BNS-1")
        query, params = retriever.graph.run_query.call_args.args
        self.assertIn("(n)<-[:BELONGS_TO*0..10]-(child)", query)
        self.assertEqual(params, {"id": "BNS-1"})
        retriever.get_ancestors("BNS-1")
        query, _ = retriever.graph.run_query.call_args.args
        self.assertIn("(n {id: $id})-[:BELONGS_TO*0..10]->(parent)", query)

    def test_bns_hierarchy_has_inverse_edges(self) -> None:
        """Every BNS HAS_* edge has a matching child-to-parent edge."""
        roman = SimpleNamespace(roman_no="i", text="roman")
        sub = SimpleNamespace(sub_clause_no="a", text="sub", roman_clauses=[roman])
        clause = SimpleNamespace(clause_no="1", text="clause", sub_clauses=[sub])
        section = SimpleNamespace(section_no="1", section_title="title", text="section", clauses=[clause], explanations=[SimpleNamespace(text="explanation")], illustrations=[SimpleNamespace(text="illustration")])
        chapter = SimpleNamespace(chapter_no="1", chapter_title="chapter", text="chapter", sections=[section])
        part = SimpleNamespace(part_no="1", title="part", text="part", chapters=[chapter])
        store = Mock()
        BNSGraphBuilder(store).build(SimpleNamespace(parts=[part]))
        edges = [entry.args for entry in store.merge_relationship.call_args_list]
        hierarchy = [(parent, child) for parent, child, kind in edges if kind.startswith("HAS_")]
        self.assertEqual(len(hierarchy), 8)
        for parent, child in hierarchy:
            self.assertIn((child, parent, "BELONGS_TO"), edges)

    def test_store_preserves_relationship_direction(self) -> None:
        """The store writes source -> target without reversing the builder."""
        store = Neo4jStore.__new__(Neo4jStore)
        store.execute = Mock()
        store.merge_relationship("child", "parent", "BELONGS_TO")
        query, params = store.execute.call_args.args
        self.assertIn("MERGE (a)-[r:BELONGS_TO]->(b)", query)
        self.assertEqual((params["source_id"], params["target_id"]), ("child", "parent"))


class RetryForwardingTests(unittest.TestCase):
    """Exercise real orchestration with the downstream signatures enforced."""

    def test_retry_options_are_not_forwarded_to_incompatible_clients(self) -> None:
        """Retrieval and context retries must not raise unexpected-keyword errors."""
        retriever = LegalRetriever.__new__(LegalRetriever)
        retriever.hybrid = Mock(spec=HybridRetriever)
        retriever.hybrid.retrieve = Mock(
            side_effect=lambda query, vector_k, rerank_k: {"reranked_results": [], "graph_context": {}}
        )
        retriever.kanoon = Mock()
        retriever.kanoon.retrieve.side_effect = lambda query, top_k: []
        result = retriever.retrieve("theft", top_k=15, threshold=0.4, include_full_docs=True)
        retriever.hybrid.retrieve.assert_called_once_with(query="theft", vector_k=15, rerank_k=5)
        retriever.kanoon.retrieve.assert_called_once_with(query="theft", top_k=5)
        self.assertIn("final_context", result)


if __name__ == "__main__":
    unittest.main()
