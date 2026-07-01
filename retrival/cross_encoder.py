from __future__ import annotations

from sentence_transformers import CrossEncoder


class LegalReranker:

    def __init__(
        self,
        model_name: str = "BAAI/bge-reranker-large"
    ):

        self.model = CrossEncoder(
            model_name,
            max_length=512
        )

    # =====================================================
    # BUILD RERANK QUERY
    # =====================================================

    def build_rerank_query(
        self,
        query: str,
        analysis=None
    ) -> str:

        if analysis is None:
            return query

        parts = [
            f"User Query: {query}"
        ]

        if getattr(
            analysis,
            "offence",
            None
        ):
            parts.append(
                f"Legal Offence: {analysis.offence}"
            )

        if getattr(
            analysis,
            "intent",
            None
        ):
            parts.append(
                f"Intent: {analysis.intent}"
            )

        return "\n".join(parts)

    # =====================================================
    # LEGAL BOOSTING
    # =====================================================

    def legal_boost(
        self,
        score: float,
        text: str,
        analysis=None
    ) -> float:

        if analysis is None:
            return score

        text = text.lower()

        boost = 0.0

        offence = getattr(
            analysis,
            "offence",
            None
        )

        intent = getattr(
            analysis,
            "intent",
            None
        )

        # offence keyword present
        if offence:

            if offence.lower() in text:
                boost += 0.15

        # punishment intent
        if intent == "punishment":

            if "shall be punished" in text:
                boost += 0.25

            if "punishment" in text:
                boost += 0.10

            if "imprisonment" in text:
                boost += 0.05

        # evidence intent
        elif intent == "evidence":

            if "evidence" in text:
                boost += 0.15

        # procedure intent
        elif intent == "procedure":

            if "procedure" in text:
                boost += 0.15

        return score + boost

    # =====================================================
    # RERANK
    # =====================================================

    def rerank(
        self,
        query: str,
        points,
        top_k: int = 5,
        analysis=None
    ):

        if not points:
            return []

        rerank_query = self.build_rerank_query(
            query=query,
            analysis=analysis
        )

        pairs = []

        point_texts = []

        for point in points:

            payload = point.payload

            text = (
                payload.get(
                    "enriched_text"
                )
                or payload.get(
                    "text",
                    ""
                )
            )

            point_texts.append(text)

            pairs.append(
                (
                    rerank_query,
                    text
                )
            )

        scores = self.model.predict(
            pairs,
            show_progress_bar=False
        )

        ranked = []

        for point, score, text in zip(
            points,
            scores,
            point_texts
        ):

            final_score = self.legal_boost(
                score=float(score),
                text=text,
                analysis=analysis
            )

            ranked.append(
                {
                    "point": point,
                    "rerank_score": float(score),
                    "final_score": float(final_score)
                }
            )

        ranked.sort(
            key=lambda x: x["final_score"],
            reverse=True
        )

        results = [
            item["point"]
            for item in ranked[:top_k]
        ]

        # =============================
        # DEBUG LOGGING
        # =============================

        print("\n" + "=" * 80)
        print("RERANK RESULTS")
        print("=" * 80)

        for rank, item in enumerate(
            ranked[:top_k],
            start=1
        ):

            point = item["point"]

            print(
                f"{rank}. "
                f"{point.payload.get('chunk_id')} "
                f"| rerank={item['rerank_score']:.4f} "
                f"| final={item['final_score']:.4f}"
            )

        print("=" * 80)

        return results