from __future__ import annotations

import logging

from retrieval.hybrid_retrieval import HybridRetriever
from retrieval.judgments import KanoonClient

logger = logging.getLogger(__name__)


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
        judgments,
        include_full_docs: bool = False
    ):
        context = []

        # -----------------------------------------
        # Statutory Retrieval
        # -----------------------------------------
        context.append("===== STATUTORY LAW =====\n")

        for point in hybrid_result["reranked_results"]:
            payload = point.payload

            if include_full_docs:
                doc_text = payload.get('document', '')
            else:
                doc_text = payload.get('text', '')

            context.append(
                f"""
DOCUMENT:
{payload.get('document')}

CHUNK:
{payload.get('chunk_id')}

TEXT:
{doc_text}
"""
            )

        # -----------------------------------------
        # Graph Expansion
        # -----------------------------------------
        context.append("\n===== KNOWLEDGE GRAPH =====\n")
        for node_id, graph_data in hybrid_result["graph_context"].items():
            context.append(f"\nNODE: {node_id}")
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
        context.append("\n===== JUDGMENTS =====\n")
        for judgment in judgments:
            context.append(str(judgment))

        return "\n".join(context)

    # =====================================================
    # RETRIEVE
    # =====================================================

    def retrieve(
        self,
        query: str,
        **kwargs
    ):
        # Extract known parameters with defaults
        vector_k = kwargs.get('vector_k', 30)
        rerank_k = kwargs.get('rerank_k', 5)
        judgment_k = kwargs.get('judgment_k', 5)
        include_full_docs = kwargs.get('include_full_docs', False)

        # Allow 'top_k' as alias for vector_k
        if 'top_k' in kwargs:
            vector_k = kwargs['top_k']

        # Forward only options supported by each retriever.
        hybrid_result = self.hybrid.retrieve(
            query=query,
            vector_k=vector_k,
            rerank_k=rerank_k
        )

        judgments = self.kanoon.retrieve(
            query=query,
            top_k=judgment_k
        )

        final_context = self.build_context(
            hybrid_result,
            judgments,
            include_full_docs=include_full_docs
        )

        return {
            "query": query,
            "statutory_results": hybrid_result["reranked_results"],
            "graph_context": hybrid_result["graph_context"],
            "judgments": judgments,
            "final_context": final_context
        }


if __name__ == "__main__":
    query = "My bike was stolen from outside my house. What punishment can the offender face?"
    retriever = LegalRetriever()
    logger.debug('%s', retriever.retrieve(query))