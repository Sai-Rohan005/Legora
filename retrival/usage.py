from __future__ import annotations

from retrival.hybrid_retrieval import HybridRetriever
from retrival.judgments import KanoonClient


class LegalRetriever:

    def __init__(self):

        self.hybrid = HybridRetriever()

        self.kanoon = KanoonClient()

    # =====================================================
    # BUILD CONTEXT
    # =====================================================

    def build_context(
        self,
        hybrid_result,
        judgments
    ):

        context = []

        # -----------------------------------------
        # Statutory Retrieval
        # -----------------------------------------

        context.append(
            "===== STATUTORY LAW =====\n"
        )

        for point in hybrid_result[
            "reranked_results"
        ]:

            payload = point.payload

            context.append(
                f"""
DOCUMENT:
{payload.get('document')}

CHUNK:
{payload.get('chunk_id')}

TEXT:
{payload.get('text')}
"""
            )

        # -----------------------------------------
        # Graph Expansion
        # -----------------------------------------

        context.append(
            "\n===== KNOWLEDGE GRAPH =====\n"
        )

        for node_id, graph_data in (
            hybrid_result[
                "graph_context"
            ].items()
        ):

            context.append(
                f"\nNODE: {node_id}"
            )

            context.append(
                f"""
Ancestors:
{graph_data['ancestors']}

Children:
{graph_data['children']}

References:
{graph_data['references']}
"""
            )

        # -----------------------------------------
        # Judgments
        # -----------------------------------------

        context.append(
            "\n===== JUDGMENTS =====\n"
        )

        for judgment in judgments:

            context.append(
                str(judgment)
            )

        return "\n".join(context)

    # =====================================================
    # RETRIEVE
    # =====================================================

    def retrieve(
        self,
        query: str,
        vector_k: int = 30,
        rerank_k: int = 5,
        judgment_k: int = 5
    ):

        # -----------------------------------------
        # Hybrid Retrieval
        # -----------------------------------------

        hybrid_result = (
            self.hybrid.retrieve(
                query=query,
                vector_k=vector_k,
                rerank_k=rerank_k
            )
        )

        # -----------------------------------------
        # Kanoon Retrieval
        # -----------------------------------------

        judgments = (
            self.kanoon.retrieve(
                query=query,
                top_k=judgment_k
            )
        )

        # -----------------------------------------
        # Final Context
        # -----------------------------------------

        final_context = (
            self.build_context(
                hybrid_result,
                judgments
            )
        )

        return {

            "query":
                query,

            "statutory_results":
                hybrid_result[
                    "reranked_results"
                ],

            "graph_context":
                hybrid_result[
                    "graph_context"
                ],

            "judgments":
                judgments,

            "final_context":
                final_context
        }