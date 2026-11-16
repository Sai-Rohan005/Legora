from retrieval.usage import LegalRetriever
from LLM.llm import LegalLLM
from evaluator.LLM_evaluator import LegalLLMEvaluator

import os
import logging
import dotenv

dotenv.load_dotenv()

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self, max_attempts: int = 3):
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self.retriever = LegalRetriever()
        self.llm = LegalLLM(api_key=os.getenv("GEMINI_API_KEY"))
        self.evaluator = LegalLLMEvaluator(api_key=os.getenv("GEMINI_API_KEY"))

        self.max_attempts = max_attempts
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
            query=self.current_query,
            answer=answer,
            context=retrieval_result
        )

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------
    def decide(self, evaluation: dict):
        score = evaluation.get("overall_score", 0)
        if score >= 80:
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
            self.retrieval_kwargs["top_k"] = self.retrieval_kwargs.get("top_k", 10) + 5
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
    def search(self, query: str):
        self.attempt = 0
        self.current_query = query   # start with original
        self.retrieval_kwargs.clear()
        self.generation_kwargs.clear()

        last_retrieval = None
        last_answer = None
        last_eval = None

        while self.attempt < self.max_attempts:
            self.attempt += 1
            logger.info("Attempt %s/%s", self.attempt, self.max_attempts)

            # 1. Retrieve (uses self.current_query + retrieval_kwargs)
            retrieval_result = self.get_context()
            last_retrieval = retrieval_result
            context = retrieval_result.get("final_context", "")

            # 2. Generate (uses self.current_query + generation_kwargs)
            answer = self.get_llm_result(context)
            last_answer = answer

            # 3. Evaluate
            evaluation = self.evaluate(answer, retrieval_result)
            last_eval = evaluation

            # 4. Decide
            decision = self.decide(evaluation)

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
            "query": self.current_query,
            "answer": last_answer,
            "retrieval": last_retrieval,
            "evaluation": last_eval,
            "status": "FAIL",
            "attempts": self.attempt
        }