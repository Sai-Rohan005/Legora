from __future__ import annotations

import logging

import json
import re
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from legora.config import EvaluationSettings, Settings, get_settings

logger = logging.getLogger(__name__)

class LegalLLMEvaluator:

    """
    LLM-as-a-Judge evaluator for Legal RAG.

    Evaluates:

        1. Correctness
        2. Faithfulness
        3. Groundedness
        4. Citation Accuracy
        5. Answer Completeness
        6. Hallucination Rate
        7. Abstention Quality

    Input:

        Question
        Generated answer
        Qdrant context
        Neo4j context
        Kanoon context
        Reference answer (optional)

    Gemini returns structured JSON.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        settings: Settings | EvaluationSettings | None = None,
    ):

        settings = settings or get_settings()
        self.api_key = api_key or (settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None)
        if not self.api_key or not self.api_key.strip():
            raise ValueError("GEMINI_API_KEY is required for judge evaluation")

        self.client = genai.Client(
            api_key=self.api_key,
            http_options=types.HttpOptions(timeout=int(settings.external_timeout_seconds * 1000), retry_options=types.HttpRetryOptions(attempts=1))
        )

        self.model = model or settings.gemini_model

    # ============================================================
    # MAIN EVALUATION
    # ============================================================

    def evaluate(
        self,
        question: str,
        answer: str,
        qdrant_context: Optional[List[Any]] = None,
        neo4j_context: Optional[List[Any]] = None,
        kanoon_context: Optional[List[Any]] = None,
        reference_answer: Optional[str] = None,
    ) -> Dict[str, Any]:

        qdrant_context = qdrant_context or []
        neo4j_context = neo4j_context or []
        kanoon_context = kanoon_context or []

        context = self._build_context(
            qdrant_context,
            neo4j_context,
            kanoon_context
        )

        return self.evaluate_context(question, answer, context, reference_answer)

    def evaluate_context(
        self, question: str, answer: str, context: str,
        reference_answer: str | None = None,
    ) -> Dict[str, Any]:
        """Judge a saved, already formatted context with the production prompt at temperature zero."""
        prompt = self._build_prompt(
            question=question,
            answer=answer,
            context=context,
            reference_answer=reference_answer
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json"
            )
        )

        return self._parse_response(
            response.text
        )

    # ============================================================
    # CONTEXT
    # ============================================================

    def _build_context(
        self,
        qdrant: List[Any],
        neo4j: List[Any],
        kanoon: List[Any]
    ) -> str:

        blocks = []

        blocks.append(
            self._format_source(
                "QDRANT",
                qdrant
            )
        )

        blocks.append(
            self._format_source(
                "NEO4J",
                neo4j
            )
        )

        blocks.append(
            self._format_source(
                "KANOON",
                kanoon
            )
        )

        return "\n\n".join(
            block
            for block in blocks
            if block.strip()
        )

    def _format_source(
        self,
        source_name: str,
        documents: List[Any]
    ) -> str:

        if not documents:
            return (
                f"===== {source_name} =====\n"
                "NO RESULTS"
            )

        output = [
            f"===== {source_name} ====="
        ]

        for i, doc in enumerate(
            documents,
            start=1
        ):

            if isinstance(doc, str):

                text = doc

            elif isinstance(doc, dict):

                text = json.dumps(
                    doc,
                    ensure_ascii=False
                )

            else:

                try:
                    text = json.dumps(
                        doc,
                        default=str,
                        ensure_ascii=False
                    )

                except Exception:

                    text = str(doc)

            output.append(
                f"[{source_name}-{i}]\n"
                f"{text}"
            )

        return "\n".join(output)

    # ============================================================
    # PROMPT
    # ============================================================

    def _build_prompt(
        self,
        question: str,
        answer: str,
        context: str,
        reference_answer: Optional[str]
    ) -> str:

        reference = (
            reference_answer
            if reference_answer
            else "NOT PROVIDED"
        )

        return f"""
You are an expert evaluator of a legal Retrieval-Augmented
Generation system.

The system retrieves legal information from:

1. Qdrant
2. Neo4j
3. Kanoon API

and generates a final answer using an LLM.

Your task is NOT to answer the legal question.

Your task is to evaluate the GENERATED ANSWER.

============================================================
QUESTION
============================================================

{question}

============================================================
GENERATED ANSWER
============================================================

{answer}

============================================================
RETRIEVED CONTEXT
============================================================

{context}

============================================================
REFERENCE ANSWER
============================================================

{reference}

============================================================
EVALUATION RULES
============================================================

Evaluate the answer claim-by-claim.

A CLAIM is a factual/legal statement that can independently
be checked against the retrieved context.

For every claim determine:

SUPPORTED
    The retrieved context directly supports the claim.

PARTIALLY_SUPPORTED
    The context supports only part of the claim.

UNSUPPORTED
    The claim cannot be supported from the retrieved context.

CONTRADICTED
    The retrieved context contradicts the claim.

Do NOT treat general legal knowledge as retrieved evidence.

============================================================
METRICS
============================================================

1. CORRECTNESS

Evaluate whether the answer is legally correct.

Score:
0 = completely incorrect
1 = mostly incorrect
2 = partially correct
3 = mostly correct
4 = fully correct

If reference answer is unavailable, judge against the
retrieved legal evidence.

------------------------------------------------------------

2. FAITHFULNESS

Measure whether the answer faithfully represents the
retrieved context.

A claim is faithful only if it is supported by the context.

Score from 0 to 100.

------------------------------------------------------------

3. GROUNDEDNESS

Measure how much of the generated answer is grounded in
retrieved evidence.

Score from 0 to 100.

Groundedness is NOT the same as correctness.

An answer can be legally plausible but poorly grounded.

------------------------------------------------------------

4. CITATION ACCURACY

Check every citation appearing in the answer.

For each citation determine:

- citation exists
- referenced source exists
- source actually supports the claim
- citation points to the correct section/document

Score from 0 to 100.

If the answer contains no citations:

citation_accuracy = 0

unless the system explicitly does not require citations.

------------------------------------------------------------

5. ANSWER COMPLETENESS

Determine whether the answer addresses all important
parts of the question that can be answered from the
retrieved context.

Score from 0 to 100.

Do not penalize the answer for information that is absent
from the retrieved context.

------------------------------------------------------------

6. HALLUCINATION RATE

Determine the percentage of factual claims that are
unsupported or contradicted by the retrieved context.

Formula:

hallucination_rate =
    hallucinated_claims / total_factual_claims * 100

------------------------------------------------------------

7. ABSTENTION QUALITY

If the retrieved context is insufficient to answer the
question, the system should explicitly say that the
available evidence is insufficient.

Evaluate:

correct_abstention = true

when the system appropriately refuses or limits its answer
because evidence is insufficient.

incorrect_abstention = true

when the system refuses despite sufficient evidence.

If the question is answerable, the evaluator should not
penalize the system for answering.

============================================================
IMPORTANT
============================================================

Do not reward verbosity.

Do not reward an answer merely because it sounds legally
plausible.

Use only the supplied retrieved context when judging
groundedness and faithfulness.

Separate:

LEGAL CORRECTNESS

from

EVIDENCE GROUNDING.

============================================================
OUTPUT
============================================================

Return ONLY valid JSON.

Use exactly this structure:

{{
    "overall_score": 0,

    "correctness": {{
        "score": 0,
        "reason": ""
    }},

    "faithfulness": {{
        "score": 0,
        "supported_claims": 0,
        "total_claims": 0,
        "reason": ""
    }},

    "groundedness": {{
        "score": 0,
        "reason": ""
    }},

    "citation_accuracy": {{
        "score": 0,
        "total_citations": 0,
        "correct_citations": 0,
        "reason": ""
    }},

    "answer_completeness": {{
        "score": 0,
        "reason": ""
    }},

    "hallucination": {{
        "rate": 0,
        "hallucinated_claims": 0,
        "total_claims": 0,
        "reason": ""
    }},

    "abstention": {{
        "applicable": false,
        "correct_abstention": false,
        "score": 0,
        "reason": ""
    }},

    "claims": [
        {{
            "claim": "",
            "status": "SUPPORTED",
            "evidence": [],
            "citation": "",
            "citation_correct": true
        }}
    ],

    "critical_errors": [],

    "summary": ""
}}

Rules:

- Scores must be numeric.
- Percentages must be between 0 and 100.
- correctness.score must be between 0 and 4.
- status must be one of:
  SUPPORTED
  PARTIALLY_SUPPORTED
  UNSUPPORTED
  CONTRADICTED

Return JSON only.
"""

    # ============================================================
    # PARSE
    # ============================================================

    def _parse_response(
        self,
        response_text: str
    ) -> Dict[str, Any]:

        text = response_text.strip()

        # Remove accidental markdown fences
        text = re.sub(
            r"^```json\s*",
            "",
            text,
            flags=re.I
        )

        text = re.sub(
            r"\s*```$",
            "",
            text
        )

        try:

            result = json.loads(text)

        except json.JSONDecodeError as e:

            raise ValueError(
                "Gemini returned invalid JSON:\n"
                + text
            ) from e

        return result


# ================================================================
# EXAMPLE
# ================================================================

if __name__ == "__main__":

    evaluator = LegalLLMEvaluator()

    question = (
        "What is the punishment for theft under "
        "Section 303 of the Bharatiya Nyaya Sanhita?"
    )

    answer = """
    Under Section 303 of the Bharatiya Nyaya Sanhita,
    theft is punishable with imprisonment of either
    description for a term which may extend to three years,
    or with fine, or with both.
    """

    qdrant_results = [
        {
            "id": "303",
            "section": "303",
            "text": (
                "Whoever commits theft shall be punished "
                "with imprisonment of either description "
                "for a term which may extend to three years, "
                "or with fine, or with both..."
            )
        }
    ]

    neo4j_results = [
        {
            "section": "303",
            "relationship": "OFFENCE",
            "text": "Theft"
        }
    ]

    kanoon_results = []

    result = evaluator.evaluate(
        question=question,
        answer=answer,
        qdrant_context=qdrant_results,
        neo4j_context=neo4j_results,
        kanoon_context=kanoon_results
    )

    logger.debug("%s", json.dumps(result, indent=4, ensure_ascii=False))
