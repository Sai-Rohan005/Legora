"""Exercise the real retry loop and select the best complete failed attempt."""

from collections.abc import Callable
from unittest.mock import patch

import pytest

from LegalRag.rag_pipeline import RAGPipeline
from legora.config import Settings


@pytest.fixture
def pipeline_factory() -> Callable[..., RAGPipeline]:
    """Mock service/model boundaries while retaining all pipeline control flow."""
    settings = Settings(
        _env_file=None, gemini_api_key="test-key", qdrant_url="http://qdrant.invalid",
        neo4j_uri="bolt://neo4j.invalid", neo4j_username="test", neo4j_password="test",
        kanoon_token="test", top_k=10, pass_threshold=80, max_attempts=3,
    )

    def create(evaluations: list[dict], budget: int = 3) -> RAGPipeline:
        """Build clients with autospec so incorrect SDK-wrapper arguments fail."""
        with patch("LegalRag.rag_pipeline.get_settings", return_value=settings), patch(
            "LegalRag.rag_pipeline.setup_logging"
        ), patch("LegalRag.rag_pipeline.LegalRetriever", autospec=True), patch(
            "LegalRag.rag_pipeline.LegalLLM", autospec=True
        ), patch("LegalRag.rag_pipeline.LegalLLMEvaluator", autospec=True):
            pipeline = RAGPipeline(max_attempts=budget)
        pipeline.retriever.retrieve.side_effect = [
            {"final_context": f"context-{index}", "statutory_results": [], "graph_context": {}, "judgments": []}
            for index in range(1, budget + 1)
        ]
        pipeline.llm.generate.side_effect = [f"answer-{index}" for index in range(1, budget + 1)]
        pipeline.evaluator.evaluate.side_effect = evaluations
        return pipeline

    return create


def evaluation(score: float, stage: str = "RETRIEVAL") -> dict:
    """Describe evaluator output used to drive a specific retry decision."""
    return {"overall_score": score, "failure_stage": stage}


def test_pass_on_first_attempt(pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """A passing first answer is returned without another retrieve or generation."""
    pipeline = pipeline_factory([evaluation(90)])
    result = pipeline.search("Article 21")
    assert (result["status"], result["attempts"], result["answer"]) == ("PASS", 1, "answer-1")
    pipeline.retriever.retrieve.assert_called_once_with("Article 21")
    pipeline.llm.generate.assert_called_once_with(query="Article 21", context="context-1")
    pipeline.evaluator.evaluate.assert_called_once_with(question="Article 21", answer="answer-1", qdrant_context=[], neo4j_context=[], kanoon_context=[])
    assert pipeline.retrieval_kwargs == {}
    assert pipeline.generation_kwargs == {}


@pytest.mark.parametrize("stage", ("RETRIEVAL", "RERANKING"))
def test_retrieval_retry_expands_query_and_increases_k(stage: str, pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """Failure feedback changes the actual second retrieval request."""
    pipeline = pipeline_factory([evaluation(20, stage), evaluation(90)])
    result = pipeline.search("theft")
    calls = pipeline.retriever.retrieve.call_args_list
    assert calls[0].args == ("theft",)
    assert calls[0].kwargs == {}
    assert calls[1].args == ("theft legal statute case law",)
    assert calls[1].kwargs["top_k"] == 15
    assert calls[1].kwargs["threshold"] == pytest.approx(0.4)
    assert result["query"] == calls[1].args[0]
    assert (result["status"], result["attempts"]) == ("PASS", 2)


def test_retrieval_retry_increases_the_requested_k(pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """An API top_k override becomes the base for retry expansion."""
    pipeline = pipeline_factory([evaluation(20), evaluation(90)])
    pipeline.search("theft", top_k=20)
    assert [entry.kwargs["top_k"] for entry in pipeline.retriever.retrieve.call_args_list] == [20, 25]


@pytest.mark.parametrize("stage", ("GENERATION", "CITATION"))
def test_generation_retry_tunes_the_next_llm_call(stage: str, pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """Generation feedback adjusts temperature and output budget, keeping the query."""
    pipeline = pipeline_factory([evaluation(30, stage), evaluation(90)])
    result = pipeline.search("Article 21")
    first, second = pipeline.llm.generate.call_args_list
    assert first.kwargs == {"query": "Article 21", "context": "context-1"}
    assert second.kwargs == {
        "query": "Article 21", "context": "context-2",
        "temperature": pytest.approx(0.5), "max_tokens": 700,
    }
    assert pipeline.retrieval_kwargs == {}
    assert result["answer"] == "answer-2"


def test_context_retry_requests_full_documents(pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """A context failure sets the retrieval option on the second attempt."""
    pipeline = pipeline_factory([evaluation(30, "CONTEXT"), evaluation(90)])
    pipeline.search("Article 21")
    assert pipeline.retriever.retrieve.call_args_list[1].kwargs == {"include_full_docs": True}


@pytest.mark.parametrize("scores,winner", [
    ([70, 40, 20], 1), ([20, 70, 30], 2), ([20, 30, 70], 3), ([60, 60, 10], 1),
])
def test_exhaustion_returns_best_attempt_with_matching_sources(scores: list[int], winner: int, pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """Return the highest-scoring complete attempt, not the last failed answer."""
    pipeline = pipeline_factory([evaluation(score) for score in scores])
    result = pipeline.search("theft")
    assert result["status"] == "FAIL"
    assert result["attempts"] == 3
    assert pipeline.attempt == 3
    assert pipeline.llm.generate.call_count == 3
    assert result["answer"] == f"answer-{winner}"
    assert result["retrieval"]["final_context"] == f"context-{winner}"
    assert result["evaluation"]["overall_score"] == scores[winner - 1]
    assert result["query"] == pipeline.retriever.retrieve.call_args_list[winner - 1].args[0]


@pytest.mark.parametrize("budget", (1, 2, 4))
def test_exhaustion_never_exceeds_budget(budget: int, pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """Every completed attempt consumes exactly one unit of the configured budget."""
    pipeline = pipeline_factory([evaluation(10)] * budget, budget=budget)
    result = pipeline.search("Article 21")
    assert result["attempts"] == budget
    assert pipeline.retriever.retrieve.call_count == budget
    assert pipeline.llm.generate.call_count == budget
    assert pipeline.evaluator.evaluate.call_count == budget
    assert len(pipeline.retrieval_kwargs) == (0 if budget == 1 else 2)


@pytest.mark.parametrize("score,expected", ((79.99, "FAIL"), (80, "PASS"), (100, "PASS")))
def test_pass_threshold_boundary(score: float, expected: str, pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """The pass threshold is inclusive and does not round sub-threshold scores up."""
    assert pipeline_factory([evaluation(score)], budget=1).search("Article 21")["status"] == expected


@pytest.mark.parametrize("query,expected", [
    ("theft", "theft legal statute case law"),
    ("Can a person seek anticipatory bail", "Can a person seek anticipatory bail relevant act section"),
    ("What is punishment under section 303", "What is punishment under section 303"),
])
def test_query_expansion_rules(query: str, expected: str, pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """Existing rule/section queries retain their specificity during expansion."""
    pipeline = pipeline_factory([evaluation(90)])
    assert pipeline._expand_query(query) == expected


def test_unsupported_citation_overrides_high_judge_score_and_retries(pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """A nominally passing judge cannot approve unsupported statutory citations."""
    pipeline = pipeline_factory([evaluation(100), evaluation(95)], budget=2)
    pipeline.llm.generate.side_effect = ["Section 999 BNS applies.", "Section 303 BNS applies."]
    context = {"final_context": "BNS-303", "statutory_results": [{"chunk_id": "BNS-303"}], "graph_context": {}, "judgments": []}
    pipeline.retriever.retrieve.side_effect = [context, context]
    result = pipeline.search("theft")
    assert result["status"] == "PASS" and result["attempts"] == 2
    assert result["citation_check"]["unsupported_citations"] == []
    assert result["citation_check"]["citation_precision"] == 1
    assert pipeline.llm.generate.call_args_list[1].kwargs["temperature"] == pytest.approx(0.5)
    assert pipeline.retriever.retrieve.call_args_list[1].args == ("theft",)


def test_exhausted_unsupported_answer_keeps_matching_flags_and_penalty(pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """The chosen best failed attempt carries its own citation report and reduced score."""
    pipeline = pipeline_factory([evaluation(100)], budget=1)
    pipeline.llm.generate.side_effect = ["Section 303 BNS and section 999 BNS."]
    pipeline.retriever.retrieve.side_effect = [{"final_context": "BNS-303", "statutory_results": [{"chunk_id": "BNS-303"}], "graph_context": {}, "judgments": []}]
    result = pipeline.search("theft")
    assert result["status"] == "FAIL"
    assert result["evaluation"]["overall_score"] == 50
    assert result["evaluation"]["llm_overall_score"] == 100
    assert result["evaluation"]["failure_stage"] == "CITATION"
    assert result["citation_check"]["unsupported_citations"] == ["BNS-999"]


def test_one_unsupported_citation_cannot_pass_even_with_high_precision(pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """The score cap enforces retry even when most citation occurrences are supported."""
    pipeline = pipeline_factory([evaluation(100)], budget=1)
    pipeline.llm.generate.side_effect = ["Section 303 BNS. " * 10 + "Section 999 BNS."]
    pipeline.retriever.retrieve.side_effect = [{"final_context": "BNS-303"}]
    result = pipeline.search("theft")
    assert result["status"] == "FAIL" and result["evaluation"]["overall_score"] == 79
    assert result["citation_check"]["citation_precision"] == pytest.approx(10 / 11)


def test_best_failed_attempt_retains_its_own_citation_flags(pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """The verifier report must describe the selected answer, not the last retry."""
    pipeline = pipeline_factory([evaluation(100), evaluation(90)], budget=2)
    pipeline.llm.generate.side_effect = ["Section 303 BNS and section 999 BNS.", "Section 888 BNS."]
    pipeline.retriever.retrieve.side_effect = [{"final_context": "BNS-303"}] * 2
    result = pipeline.search("theft")
    assert result["answer"] == "Section 303 BNS and section 999 BNS."
    assert result["citation_check"]["unsupported_citations"] == ["BNS-999"]
    assert result["evaluation"]["overall_score"] == 50
    assert result["attempts"] == 2


def test_unsupported_citations_cannot_pass_at_zero_threshold(pipeline_factory: Callable[..., RAGPipeline]) -> None:
    """The explicit decision guard is required even when a score cap cannot go below zero."""
    pipeline = pipeline_factory([evaluation(100)], budget=1)
    pipeline.settings = pipeline.settings.model_copy(update={"pass_threshold": 0})
    pipeline.llm.generate.side_effect = ["Section 999 BNS."]
    result = pipeline.search("theft")
    assert result["status"] == "FAIL"
