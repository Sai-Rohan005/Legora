from sentence_transformers import CrossEncoder
from typing import List, Dict


class LegalReranker:

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ):
        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 5
    ) -> List[Dict]:

        if not results:
            return []

        # build (query, document) pairs
        pairs = [
            (query, r["text"])
            for r in results
        ]

        # predict relevance scores
        scores = self.model.predict(pairs)

        # attach scores
        for r, s in zip(results, scores):
            r["rerank_score"] = float(s)

        # sort by rerank score
        results.sort(
            key=lambda x: x["rerank_score"],
            reverse=True
        )

        return results[:top_k]