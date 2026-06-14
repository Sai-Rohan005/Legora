from __future__ import annotations

from sentence_transformers import CrossEncoder


class LegalReranker:

    def __init__(
        self,
        model_name: str =
        "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):

        self.model = CrossEncoder(
            model_name
        )

    # =====================================================
    # RERANK
    # =====================================================

    def rerank(
        self,
        query: str,
        points,
        top_k: int = 5
    ):

        if not points:
            return []

        pairs = []

        for point in points:

            payload = point.payload

            text = (
                payload.get(
                    "enriched_text"
                )
                or
                payload.get(
                    "text",
                    ""
                )
            )

            pairs.append(
                (
                    query,
                    text
                )
            )

        scores = (
            self.model.predict(
                pairs
            )
        )

        ranked = []

        for point, score in zip(
            points,
            scores
        ):

            ranked.append(
                (
                    float(score),
                    point
                )
            )

        ranked.sort(
            key=lambda x: x[0],
            reverse=True
        )

        return [
            point
            for score, point
            in ranked[:top_k]
        ]