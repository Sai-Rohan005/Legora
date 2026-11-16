from retrieval.usage import LegalRetriever
from LLM.llm import LegalLLM
from evaluator.LLM_evaluator import LegalLLMEvaluator

import logging
from legora.config import get_settings
from legora.logging import attempt_number, log_stage, query_context, setup_logging, stage_timings

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self, max_attempts: int | None = None) -> None:
        """Configure the pipeline and initialize its external clients."""
        if max_attempts is not None and max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.settings = get_settings()
        setup_logging(self.settings.log_level)
        self.retriever = LegalRetriever()
        self.llm = LegalLLM()
        self.evaluator = LegalLLMEvaluator()

        self.max_attempts = max_attempts if max_attempts is not None else self.settings.max_attempts
        self.attempt = 0
        self.current_query = ""   # will hold the active (possibly expanded) query

        # Adjustable parameters
        self.retrieval_kwargs = {}
        self.generation_kwargs = {}

    # ------------------------------------------------------------------
    # Retrieval (uses self.current_query)
    # ------------------------------------------------------------------
    def get_context(self):
        """Retrieve using the current (possibly enhanced) query."""
        return self.retriever.retrieve(self.current_query, **self.retrieval_kwargs)

    # ------------------------------------------------------------------
    # LLM Generation
    # ------------------------------------------------------------------
    def get_llm_result(self, context: str):
        return self.llm.generate(
            query=self.current_query,
            context=context,
            **self.generation_kwargs
        )

    # ------------------------------------------------------------------
    # Evaluation
    # ------------------------------------------------------------------
    def evaluate(self, answer: str, retrieval_result: dict):
        return self.evaluator.evaluate(
            question=self.current_query,
            answer=answer,
            qdrant_context=retrieval_result.get("statutory_results", []),
            neo4j_context=list(retrieval_result.get("graph_context", {}).values()),
            kanoon_context=retrieval_result.get("judgments", [])
        )

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------
    def decide(self, evaluation: dict):
        score = evaluation.get("overall_score", 0)
        if score >= self.settings.pass_threshold:
            return {"status": "PASS", "action": "RETURN_ANSWER"}
        return {"status": "FAIL", "action": evaluation.get("recommended_action", "RETRY")}

    # ------------------------------------------------------------------
    # Failure Adjustment (NO LLM CALLS)
    # ------------------------------------------------------------------
    def _expand_query(self, query: str) -> str:
        """
        Rule-based query expansion for legal domain.
        No LLM call – purely string manipulation.
        """
        legal_terms = ["legal", "statute", "case law", "precedent", "judgment", "ruling"]
        # If query is short, add generic legal context
        if len(query.split()) < 5:
            return f"{query} legal statute case law"
        # If missing key terms, append them
        if not any(term in query.lower() for term in ["act", "section", "rule", "code"]):
            return f"{query} relevant act section"
        return query

    def adjust_for_retry(self, evaluation: dict) -> None:
        """Tune the next attempt without changing the search-owned counter."""
        stage = evaluation.get("failure_stage", "UNKNOWN")

        # ---- EARLIEST STAGE: RETRIEVAL ----
        if stage in ("RETRIEVAL", "RERANKING"):
            # 1. Expand the query (no LLM)
            expanded = self._expand_query(self.current_query)
            if expanded != self.current_query:
                logger.debug("Expanded retrieval query")
                self.current_query = expanded

            # 2. Tune retrieval parameters
            self.retrieval_kwargs["top_k"] = self.retrieval_kwargs.get("top_k", self.settings.top_k) + 5
            self.retrieval_kwargs["threshold"] = self.retrieval_kwargs.get("threshold", 0.5) - 0.1
            logger.debug("Retrieval adjusted: %s", self.retrieval_kwargs)

        # ---- MIDDLE STAGE: CONTEXT ----
        elif stage == "CONTEXT":
            self.retrieval_kwargs["include_full_docs"] = True
            logger.debug("Context adjusted: %s", self.retrieval_kwargs)

        # ---- LATER STAGES: GENERATION / CITATION ----
        elif stage in ("GENERATION", "CITATION"):
            self.generation_kwargs["temperature"] = self.generation_kwargs.get("temperature", 0.7) - 0.2
            self.generation_kwargs["max_tokens"] = self.generation_kwargs.get("max_tokens", 500) + 200
            logger.debug("Generation adjusted: %s", self.generation_kwargs)

        else:
            # Generic fallback
            self.generation_kwargs["temperature"] = self.generation_kwargs.get("temperature", 0.7) * 0.9
            logger.debug("Applied generic retry adjustment")

    # ------------------------------------------------------------------
    # Main Search with Retry Loop
    # ------------------------------------------------------------------
    def search(
        self, query: str, top_k: int | None = None,
        include_graph: bool = True, include_judgments: bool = True
    ) -> dict:
        """Run one query under a unique request ID, restoring context on exit."""
        with query_context():
            with log_stage("query") as metrics:
                result = self._search(query, top_k, include_graph, include_judgments)
                retrieval = result.get("retrieval") or {}
                metrics.candidate_count = (
                    len(retrieval.get("statutory_results", []))
                    + len(retrieval.get("judgments", []))
                )
                timings = stage_timings.get() or {}
                result["latency_ms"] = {
                    "analysis": round(timings.get("query_analysis", 0), 3),
                    "retrieval": round(timings.get("vector_search", 0) + timings.get("judgments", 0), 3),
                    "rerank": round(timings.get("reranking", 0), 3),
                    "graph": round(timings.get("graph_expansion", 0), 3),
                    "generation": round(timings.get("generation", 0), 3),
                    "judge": round(timings.get("evaluation", 0), 3),
                }
                return result

    def _search(
        self, query: str, top_k: int | None, include_graph: bool, include_judgments: bool
    ) -> dict:
        """Retry within the query context, retaining the first highest-scoring attempt."""
        self.attempt = 0
        self.current_query = query   # start with original
        self.retrieval_kwargs.clear()
        self.generation_kwargs.clear()
        if top_k is not None:
            self.retrieval_kwargs["top_k"] = top_k
        if not include_graph:
            self.retrieval_kwargs["include_graph"] = False
        if not include_judgments:
            self.retrieval_kwargs["include_judgments"] = False

        best_result: dict = {}
        best_score = float("-inf")

        while self.attempt < self.max_attempts:
            self.attempt += 1
            attempt_number.set(self.attempt)
            logger.info("Attempt %s/%s", self.attempt, self.max_attempts)

            # 1. Retrieve (uses self.current_query + retrieval_kwargs)
            with log_stage("retrieval") as metrics:
                retrieval_result = self.get_context()
                metrics.candidate_count = len(retrieval_result.get("statutory_results", [])) + len(retrieval_result.get("judgments", []))
            context = retrieval_result.get("final_context", "")

            # 2. Generate (uses self.current_query + generation_kwargs)
            with log_stage("generation", metrics.candidate_count):
                answer = self.get_llm_result(context)

            # 3. Evaluate
            with log_stage("evaluation", metrics.candidate_count):
                evaluation = self.evaluate(answer, retrieval_result)

            # 4. Decide
            decision = self.decide(evaluation)
            score = evaluation.get("overall_score", 0)
            if score > best_score:
                best_score = score
                best_result = {
                    "query": self.current_query,
                    "answer": answer,
                    "retrieval": retrieval_result,
                    "evaluation": evaluation,
                }

            if decision["status"] == "PASS":
                logger.info("Answer passed evaluation")
                return {
                    "query": self.current_query,
                    "answer": answer,
                    "retrieval": retrieval_result,
                    "evaluation": evaluation,
                    "status": "PASS",
                    "attempts": self.attempt
                }

            # 5. Failure -> adjust (no LLM calls here)
            logger.info("Attempt %s failed evaluation", self.attempt)
            if self.attempt < self.max_attempts:
                self.adjust_for_retry(evaluation)

        # Exhausted
        logger.warning("All %s attempts failed evaluation", self.max_attempts)
        return {
            **best_result,
            "status": "FAIL",
            "attempts": self.attempt
        }

    def close(self) -> None:
        """Release the clients owned by the startup-loaded pipeline."""
        self.retriever.hybrid.graph.close()
        self.retriever.hybrid.vector_db.client.close()
        self.retriever.hybrid.analyser.client.close()
        self.retriever.kanoon.rewriter.client.close()
        self.llm.client.close()
        self.evaluator.client.close()
