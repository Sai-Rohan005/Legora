"""Verify deadlines are attached at external-call boundaries."""

from unittest.mock import Mock, patch

import test_audit
from db.neo4j_store import Neo4jStore
from db.vector_store import QdrantStore
from retrieval.judgments import KanoonClient


class ExternalTimeoutTests(test_audit.ConfiguredTestCase):
    """Use real wrappers with mocked SDK transports."""

    def test_gemini_clients_have_deadlines_and_no_sdk_retries(self) -> None:
        """All four Gemini clients bound calls in milliseconds."""
        from LLM.llm import LegalLLM
        from LegalRag.query_analyser import Analyser
        from evaluator.LLM_evaluator import LegalLLMEvaluator

        with patch("google.genai.Client") as client:
            LegalLLM()
            Analyser()
            LegalLLMEvaluator()
            KanoonClient()
        self.assertEqual(client.call_count, 4)
        for entry in client.call_args_list:
            self.assertEqual(entry.kwargs["http_options"].timeout, 30000)
            self.assertEqual(entry.kwargs["http_options"].retry_options.attempts, 1)

    def test_qdrant_timeout(self) -> None:
        """Qdrant queries and health probes use a bounded SDK client."""
        with patch("db.vector_store.QdrantClient") as client:
            QdrantStore()
        self.assertEqual(client.call_args.kwargs["timeout"], 30)

    def test_neo4j_query_timeout(self) -> None:
        """Every store query receives a server-side execution deadline."""
        store = Neo4jStore.__new__(Neo4jStore)
        store.timeout = 2
        store.driver = Mock()
        session = Mock()
        session.run.return_value = []
        store.driver.session.return_value.__enter__ = Mock(return_value=session)
        store.driver.session.return_value.__exit__ = Mock(return_value=False)
        store.execute("RETURN 1")
        query = session.run.call_args.args[0]
        self.assertEqual(query.text, "RETURN 1")
        self.assertEqual(query.timeout, 2)

    def test_kanoon_http_deadlines_and_status_checks(self) -> None:
        """Both judgment endpoints enforce timeouts and reject HTTP failures."""
        client = KanoonClient.__new__(KanoonClient)
        client.headers = {"Authorization": "Token example-token"}
        with patch("retrieval.judgments.requests.post") as post, patch("retrieval.judgments.requests.get") as get:
            client.search("question")
            client.get_document("123")
        self.assertEqual(post.call_args.kwargs["timeout"], 30)
        self.assertEqual(get.call_args.kwargs["timeout"], 30)
        post.return_value.raise_for_status.assert_called_once_with()
        get.return_value.raise_for_status.assert_called_once_with()
