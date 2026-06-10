from typing import List, Dict, Any
import numpy as np


class HybridRetriever:

    def __init__(self, embedder, qdrant, graph):
        self.embedder = embedder
        self.qdrant = qdrant
        self.graph = graph

    # -----------------------------
    # MAIN SEARCH
    # -----------------------------
    def search(self, query: str, limit: int = 5):

        # 1. VECTOR SEARCH (Qdrant)
        vector_results = self._vector_search(query, limit)

        # 2. GRAPH SEARCH (Neo4j)
        graph_results = self._graph_search(query)

        # 3. MERGE RESULTS
        return self._merge_results(vector_results, graph_results)

    # -----------------------------
    # VECTOR SEARCH
    # -----------------------------
    def _vector_search(self, query: str, limit: int):

        query_embedding = self.embedder.model.encode(
            query,
            normalize_embeddings=True
        ).tolist()

        results = self.qdrant.search(
            query_vector=query_embedding,
            limit=limit
        )

        return [
            {
                "source": "vector",
                "text": r.payload.get("embedding_text"),
                "metadata": r.payload,
                "score": r.score
            }
            for r in results
        ]

    # -----------------------------
    # GRAPH SEARCH (simple Cypher fallback)
    # -----------------------------
    def _graph_search(self, query: str):

        cypher = """
        MATCH (n:LegalChunk)
        WHERE toLower(n.embedding_text) CONTAINS toLower($query)
        RETURN n.embedding_text AS text,
               n.metadata AS metadata
        LIMIT 5
        """

        with self.graph.driver.session() as session:
            result = session.run(cypher, query=query)

            return [
                {
                    "source": "graph",
                    "text": record["text"],
                    "metadata": record["metadata"]
                }
                for record in result
            ]

    # -----------------------------
    # MERGE + RERANK
    # -----------------------------
    def _merge_results(self, vector_results, graph_results):

        all_results = vector_results + graph_results

        # simple dedup by text
        seen = set()
        unique = []

        for r in all_results:
            key = r["text"]
            if key not in seen:
                seen.add(key)
                unique.append(r)

        # optional: boost vector results
        for r in unique:
            if r["source"] == "vector":
                r["score"] = r.get("score", 0) + 0.1

        # sort by score if exists
        unique.sort(
            key=lambda x: x.get("score", 0),
            reverse=True
        )

        return unique