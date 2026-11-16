from __future__ import annotations

import logging

from legora.config import get_settings
from legora.logging import log_stage
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
        settings = get_settings()
        # Extract known parameters with defaults
        vector_k = kwargs.get('vector_k', settings.top_k)
        rerank_k = kwargs.get('rerank_k', settings.rerank_k)
        judgment_k = kwargs.get('judgment_k', settings.judgment_k)
        include_full_docs = kwargs.get('include_full_docs', False)

        # Allow 'top_k' as alias for vector_k
        if 'top_k' in kwargs:
            vector_k = kwargs['top_k']

        # Forward only options supported by each retriever.
        graph_options = {} if kwargs.get("include_graph", True) else {"include_graph": False}
        hybrid_result = self.hybrid.retrieve(
            query=query,
            vector_k=vector_k,
            rerank_k=rerank_k,
            **graph_options
        )

        judgments = []
        if kwargs.get("include_judgments", True):
            with log_stage("judgments") as metrics:
                judgments = self.kanoon.retrieve(
                    query=query,
                    top_k=judgment_k
                )
                metrics.candidate_count = len(judgments)

        final_context = self.build_context(
            hybrid_result,
            judgments,
            include_full_docs=include_full_docs
        )

        return {
            "query": query,
            "statutory_results": hybrid_result["reranked_results"],
            "vector_results": hybrid_result.get("vector_results", []),
            "node_ids": hybrid_result.get("node_ids", []),
            "graph_context": hybrid_result["graph_context"],
            "judgments": judgments,
            "final_context": final_context
        }


if __name__ == "__main__":
    query = "My bike was stolen from outside my house. What punishment can the offender face?"
    retriever = LegalRetriever()
    logger.debug('%s', retriever.retrieve(query))