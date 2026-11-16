"""Configuration and query telemetry regression coverage without live services."""

import io
import json
import logging
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pydantic import ValidationError

import test_audit
from legora.config import Settings, get_settings
from legora.logging import (
    JsonFormatter, attempt_number, log_stage, query_context, request_id, setup_logging,
)
from LegalRag.rag_pipeline import RAGPipeline
from retrieval.usage import LegalRetriever
from retrieval.hybrid_retrieval import HybridRetriever


class SettingsTests(test_audit.ConfiguredTestCase):
    """Check settings precedence, validation, defaults, and secret masking."""

    def test_environment_overrides_dotenv(self) -> None:
        """Environment values win over a supplied dotenv file."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("TOP_K=12\nGEMINI_MODEL=file-model\n", encoding="utf-8")
            with patch.dict(os.environ, {"TOP_K": "17"}):
                settings = Settings(_env_file=path)
        self.assertEqual(settings.top_k, 17)
        self.assertEqual(settings.gemini_model, "file-model")

    def test_invalid_limits_and_secrets_are_rejected_safely(self) -> None:
        """Reject invalid budgets and credentials without displaying inputs."""
        for name, value in (("TOP_K", "0"), ("RERANK_K", "0"), ("MAX_ATTEMPTS", "0"), ("PASS_THRESHOLD", "101"), ("PASS_THRESHOLD", "-1"), ("LOG_LEVEL", "invalid"), ("GEMINI_API_KEY", " "), ("NEO4J_PASSWORD", "")):
            with self.subTest(name=name), patch.dict(os.environ, {name: value}):
                with self.assertRaises(ValidationError) as error:
                    Settings()
                self.assertNotIn("example-secret", str(error.exception))
                self.assertNotIn("input_value", str(error.exception))
        settings = get_settings()
        for value in ("example-gemini-key", "example-secret", "example-kanoon-token"):
            self.assertNotIn(value, repr(settings))

    def test_optional_qdrant_key_and_legacy_case(self) -> None:
        """Blank optional keys and the existing lowercase token name work."""
        env = dict(test_audit.TEST_ENV)
        env.pop("KANOON_TOKEN")
        env.update(kanoon_token="legacy-token", QDRANT_API_KEY="")
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
        self.assertIsNone(settings.qdrant_api_key)
        self.assertEqual(settings.kanoon_token.get_secret_value(), "legacy-token")

    def test_defaults_reach_pipeline_and_retrievers(self) -> None:
        """Configured limits control retrieval, passing, and retry budgets."""
        with patch.dict(os.environ, {"TOP_K": "7", "RERANK_K": "2", "JUDGMENT_K": "1", "MAX_ATTEMPTS": "4", "PASS_THRESHOLD": "95"}), patch("LegalRag.rag_pipeline.LegalRetriever"), patch("LegalRag.rag_pipeline.LegalLLM"), patch("LegalRag.rag_pipeline.LegalLLMEvaluator"):
            pipeline = RAGPipeline()
            self.assertEqual(pipeline.max_attempts, 4)
            self.assertEqual(pipeline.decide({"overall_score": 90})["status"], "FAIL")
            pipeline.adjust_for_retry({"failure_stage": "RETRIEVAL"})
            self.assertEqual(pipeline.retrieval_kwargs["top_k"], 12)
            retriever = LegalRetriever.__new__(LegalRetriever)
            retriever.hybrid = Mock()
            retriever.hybrid.retrieve.return_value = {"reranked_results": [], "graph_context": {}}
            retriever.kanoon = Mock()
            retriever.kanoon.retrieve.return_value = []
            retriever.retrieve("question")
        retriever.hybrid.retrieve.assert_called_once_with(query="question", vector_k=7, rerank_k=2)
        retriever.kanoon.retrieve.assert_called_once_with(query="question", top_k=1)

    def test_gemini_clients_share_the_configured_model(self) -> None:
        """Generation, analysis, judging, and judgment rewriting use GEMINI_MODEL."""
        from LLM.llm import LegalLLM
        from LegalRag.query_analyser import Analyser
        from evaluator.LLM_evaluator import LegalLLMEvaluator
        from retrieval.judgments import KanoonClient

        with patch.dict(os.environ, {"GEMINI_MODEL": "configured-model"}), patch("google.genai.Client"):
            clients = (LegalLLM(), Analyser(), LegalLLMEvaluator(), KanoonClient().rewriter)
        self.assertEqual([client.model for client in clients], ["configured-model"] * 4)


class LoggingTests(test_audit.ConfiguredTestCase):
    """Verify JSON fields, failure behavior, and concurrent request isolation."""

    def setUp(self) -> None:
        """Capture formatted stage logs at emission time."""
        super().setUp()
        self.output = io.StringIO()
        handler = logging.StreamHandler(self.output)
        handler.setFormatter(JsonFormatter())
        logger = logging.getLogger("legora.logging")
        previous_level = logger.level
        logger.setLevel(logging.INFO)
        self.addCleanup(logger.setLevel, previous_level)
        for name, value in (("handlers", [handler]), ("propagate", False)):
            override = patch.object(logger, name, value)
            override.start()
            self.addCleanup(override.stop)

    def records(self) -> list[dict]:
        """Read the captured newline-delimited JSON objects."""
        return [json.loads(line) for line in self.output.getvalue().splitlines()]

    def test_retry_stages_share_request_id_and_increment_attempt(self) -> None:
        """Every actual attempt records timing and source counts under one ID."""
        pipeline = test_audit.RetryTests().make_pipeline(2, "RETRIEVAL")
        pipeline.retriever.retrieve.return_value = {"final_context": "private context", "statutory_results": ["source"], "graph_context": {}, "judgments": ["case"]}
        pipeline.search("private query")
        records = self.records()
        self.assertEqual(len({record["request_id"] for record in records}), 1)
        self.assertTrue(records[0]["request_id"])
        self.assertEqual([record["attempt"] for record in records if record["stage"] == "generation"], [1, 2])
        self.assertEqual({record["stage"] for record in records}, {"retrieval", "generation", "evaluation", "query"})
        for record in records:
            self.assertEqual(record["candidate_count"], 2)
            self.assertGreaterEqual(record["latency_ms"], 0)
        self.assertIsNone(request_id.get())
        self.assertEqual(attempt_number.get(), 0)
        self.assertNotIn("private query", self.output.getvalue())
        self.assertNotIn("private context", self.output.getvalue())
        pipeline.evaluator.evaluate.assert_called_with(
            question=pipeline.current_query, answer="answer", qdrant_context=["source"],
            neo4j_context=[], kanoon_context=["case"]
        )

    def test_failed_stage_logs_type_without_secret_exception_message(self) -> None:
        """Failure telemetry must not expose SDK exceptions containing keys."""
        with self.assertRaises(RuntimeError), query_context():
            with log_stage("generation"):
                raise RuntimeError("API key: example-secret")
        record = self.records()[0]
        self.assertEqual(record["status"], "error")
        self.assertEqual(record["error_type"], "RuntimeError")
        self.assertNotIn("example-secret", self.output.getvalue())
        self.assertIsNone(request_id.get())

    def test_retrieval_substages_report_real_output_counts(self) -> None:
        """Exercise orchestration with only external retrieval/model calls mocked."""
        pipeline = test_audit.RetryTests().make_pipeline(1, "RETRIEVAL")
        hybrid = HybridRetriever.__new__(HybridRetriever)
        hybrid.analyser = Mock()
        hybrid.analyser.analyze_query.return_value = SimpleNamespace(
            offence=None, legal_concepts=["theft"], acts=["BNS"]
        )
        points = [SimpleNamespace(payload={"chunk_id": f"BNS-{number}", "text": "source"}, score=1.0) for number in (1, 2)]
        hybrid.vector_search_filtered = Mock(return_value=points)
        hybrid.reranker = Mock()
        hybrid.reranker.rerank.return_value = points[:1]
        hybrid.graph = Mock()
        hybrid.graph.run_query.return_value = []
        retriever = LegalRetriever.__new__(LegalRetriever)
        retriever.hybrid = hybrid
        retriever.kanoon = Mock()
        retriever.kanoon.retrieve.return_value = [{"title": "judgment"}]
        pipeline.retriever = retriever
        pipeline.evaluator.evaluate.return_value = {"overall_score": 90}
        pipeline.search("question")
        counts = {record["stage"]: record["candidate_count"] for record in self.records()}
        self.assertEqual(counts, {
            "query_analysis": None, "vector_search": 2, "reranking": 1,
            "graph_expansion": 1, "judgments": 1, "retrieval": 2,
            "generation": 2, "evaluation": 2, "query": 2,
        })

    def test_query_failure_restores_context(self) -> None:
        """An external failure emits correlated stage/query errors and unwinds."""
        pipeline = test_audit.RetryTests().make_pipeline(1, "RETRIEVAL")
        pipeline.retriever.retrieve.side_effect = RuntimeError("example-secret")
        with self.assertRaises(RuntimeError):
            pipeline.search("private question")
        records = self.records()
        self.assertEqual([record["stage"] for record in records], ["retrieval", "query"])
        self.assertTrue(all(record["status"] == "error" for record in records))
        self.assertEqual(len({record["request_id"] for record in records}), 1)
        self.assertNotIn("example-secret", self.output.getvalue())
        self.assertIsNone(request_id.get())
        self.assertEqual(attempt_number.get(), 0)

    def test_concurrent_queries_have_distinct_contexts(self) -> None:
        """Interleaved workers retain their own IDs and attempt numbers."""
        barrier = Barrier(2)

        def run(attempt: int) -> str:
            """Emit a stage after both query contexts are active."""
            with query_context() as identifier:
                attempt_number.set(attempt)
                barrier.wait(timeout=5)
                with log_stage("worker", attempt):
                    pass
                return identifier

        with ThreadPoolExecutor(max_workers=2) as pool:
            identifiers = list(pool.map(run, (1, 2)))
        self.assertEqual(len(set(identifiers)), 2)
        self.assertEqual({record["request_id"] for record in self.records()}, set(identifiers))
        self.assertEqual({record["attempt"] for record in self.records()}, {1, 2})
        self.assertIsNone(request_id.get())

    def test_setup_is_idempotent_and_emits_json(self) -> None:
        """Repeated app initialization produces one structured console event."""
        root = logging.getLogger()
        with patch.object(root, "handlers", []), patch.object(root, "level", root.level), patch("sys.stderr", self.output):
            setup_logging()
            setup_logging()
            self.assertEqual(len(root.handlers), 1)
            logging.getLogger("LegalRag.rag_pipeline").info("Ready")
        self.assertEqual(self.records()[0]["message"], "Ready")
