from __future__ import annotations

import logging
from threading import Lock
from typing import Any

from legora.config import get_settings
from retrieval.lexical import BM25Retriever, explicit_provisions, prepend_exact, reciprocal_rank_fusion
from legora.logging import log_stage
from db.embedder import LegalEmbedder
from db.vector_store import QdrantStore
from db.neo4j_store import Neo4jStore
from retrieval.cross_encoder import LegalReranker
from LegalRag.query_analyser import Analyser

logger = logging.getLogger(__name__)


class HybridRetriever:

    def __init__(self, use_bm25: bool | None = None, exact_id_lookup: bool | None = None) -> None:
        """Validate graph configuration before loading retrieval models."""
        settings = get_settings()
        self.use_bm25 = settings.use_bm25 if use_bm25 is None else use_bm25
        configured_lookup = settings.exact_id_lookup if exact_id_lookup is None else exact_id_lookup
        self.exact_id_lookup = self.use_bm25 if configured_lookup is None else configured_lookup
        self._bm25: BM25Retriever | None = None
        self._bm25_lock = Lock()
        self.graph = Neo4jStore()

        self.embedder = LegalEmbedder()
        self.reranker = LegalReranker()
        self.analyser=Analyser()

        self.vector_db = QdrantStore(
            collection_name="legal_rag"
        )
        if self.use_bm25:
            self.get_bm25()

    def get_bm25(self) -> BM25Retriever:
        """Build the lexical snapshot once per retriever; recreate it after corpus updates."""
        with self._bm25_lock:
            if self._bm25 is None:
                self._bm25 = BM25Retriever(self.vector_db.iter_chunks())
        return self._bm25

    def exact_matches(self, query: str) -> list[Any]:
        """Resolve explicitly named provisions through real stored chunk-ID lookups."""
        requests = explicit_provisions(query)
        if not requests:
            return []
        identifiers = list(dict.fromkeys(identifier for aliases in requests for identifier in aliases))
        found = {point.payload["chunk_id"]: point for point in self.vector_db.lookup_chunk_ids(identifiers)}
        return [next(found[value] for value in aliases if value in found)
                for aliases in requests if any(value in found for value in aliases)]

    def fuse_candidates(
        self, query: str, points: list[Any], document: str | None, limit: int,
        use_bm25: bool, exact_id_lookup: bool,
    ) -> tuple[list[Any], list[Any]]:
        """Fuse dense/BM25 ranks before reranking and protect exact hits from truncation."""
        dense = sorted(self.dedupe_points(points), key=lambda point: (-float(point.score), point.payload["chunk_id"]))[:limit]
        fused = reciprocal_rank_fusion([dense, self.get_bm25().search(query, document=document, k=limit)], k=60, limit=limit) if use_bm25 else dense
        exact = self.exact_matches(query)[:max(0, limit)] if exact_id_lookup else []
        return prepend_exact(fused, exact, limit), exact

    # =====================================================
    # VECTOR SEARCH
    # =====================================================

    def vector_search(self, query: str, k: int = 10):

        query_vector = self.embedder.embed_query(query)

        result = self.vector_db.search(
            query_vector=query_vector,
            limit=k
        )

        return result.points

    # =====================================================
    # ROOT EXTRACTION (FIXED)
    # =====================================================

    def extract_ids(self, points) -> list[str]:
        """Map current and legacy chunk identifiers to unique graph root IDs."""

        ids = set()

        for point in points:

            payload = point.payload
            chunk_id = payload.get("chunk_id")

            if not chunk_id:
                continue

            # Safer root extraction for all document types
            # Examples:
            # BSA-115(2)(a)
            # BNSS-45
            # CONST-21(PROVISO-1)

            if chunk_id.startswith("article_"):
                root_id = f"CONST-{chunk_id.split('_')[1]}"
            else:
                root_id = chunk_id.split("(")[0].split("-EXP")[0].split("-ILL")[0]

            ids.add(root_id)

        return list(ids)

    # =====================================================
    # ANCESTORS (UPWARD TRAVERSAL)
    # =====================================================

    def get_ancestors(self, node_id: str):

        query = """
        MATCH p = (n {id: $id})-[:BELONGS_TO*0..10]->(parent)
        RETURN p
        """

        return self.graph.run_query(query, {"id": node_id})

    # =====================================================
    # CHILDREN (DOWNWARD TRAVERSAL)
    # =====================================================

    def get_children(self, node_id: str):

        query = """
        MATCH p = (n)<-[:BELONGS_TO*0..10]-(child)
        WHERE n.id = $id
        RETURN p
        """

        return self.graph.run_query(query, {"id": node_id})

    # =====================================================
    # REFERENCES (UNCHANGED)
    # =====================================================

    def get_references(self, node_id: str):

        query = """
        MATCH (n {id: $id})-[:REFERENCES]->(ref)
        RETURN ref
        """

        return self.graph.run_query(query, {"id": node_id})

    # =====================================================
    # GRAPH EXPANSION
    # =====================================================

    def expand_graph(self, node_ids):

        graph_context = {}

        for node_id in node_ids:

            graph_context[node_id] = {

                "ancestors": self.get_ancestors(node_id),
                "children": self.get_children(node_id),
                "references": self.get_references(node_id)
            }

        return graph_context
    

    def build_retrieval_queries(
        self,
        analysis
    ):

        queries = []

        offence = analysis.offence

        if offence:

            queries.extend([
                offence,
                f"{offence} punishment",
                f"{offence} offence",
                f"whoever commits {offence}",
                f"{offence} shall be punished"
            ])

        queries.extend(
            analysis.legal_concepts
        )

        return list(
            dict.fromkeys(
                q.lower().strip()
                for q in queries
                if q.strip()
            )
        )
        
    def dedupe_points(self, points):

        best_points = {}

        for point in points:

            chunk_id = point.payload.get(
                "chunk_id"
            )

            if not chunk_id:
                continue

            if (
                chunk_id not in best_points
                or
                point.score >
                best_points[chunk_id].score
            ):
                best_points[chunk_id] = point

        return list(best_points.values())
    
    def vector_search_filtered(
        self,
        query: str,
        document: str | None = None,
        k: int = 10
    ):

        query_vector = self.embedder.embed_query(query)

        result = self.vector_db.search_with_filter(
            query_vector=query_vector,
            document=document,
            limit=k
        )

        return result.points
    
    def get_document_filter(
        self,
        analysis
    ):

        if not analysis.acts:
            return None

        act = analysis.acts[0].strip().lower()

        mapping = {
            "bns": "bns",
            "bnss": "bnss",
            "bsa": "bsa",
            "constitution": "constitution"
        }

        return mapping.get(act)

    # =====================================================
    # HYBRID RETRIEVE
    # =====================================================

    def retrieve(self, query: str, vector_k: int | None = None, rerank_k: int | None = None, include_graph: bool = True):

        settings = get_settings()
        vector_k = vector_k if vector_k is not None else settings.top_k
        rerank_k = rerank_k if rerank_k is not None else settings.rerank_k
        with log_stage("query_analysis"):
            analysis = self.analyser.analyze_query(query)

        queries = self.build_retrieval_queries(
            analysis
        )

        points = []

        document_filter = self.get_document_filter(
            analysis
        )

        logger.debug("Document filter: %s", document_filter)

        with log_stage("vector_search") as metrics:
            for q in queries:

                results = self.vector_search_filtered(
                    query=q,
                    document=document_filter,
                    k=vector_k
                )

                points.extend(results)

            points=self.dedupe_points(points)
            logger.debug("Retrieved %s unique vector results", len(points))
            metrics.candidate_count = len(points)

        dense_points = points
        exact = []
        if getattr(self, "use_bm25", False) or getattr(self, "exact_id_lookup", False):
            with log_stage("lexical_fusion") as metrics:
                points, exact = self.fuse_candidates(
                    query, points, document_filter, vector_k,
                    getattr(self, "use_bm25", False), getattr(self, "exact_id_lookup", False),
                )
                metrics.candidate_count = len(points)

        # Rerank
        with log_stage("reranking") as metrics:
            reranked_points = self.reranker.rerank(
                query=query,
                points=points,
                top_k=rerank_k,
                analysis=analysis
            )
            if exact:
                reranked_points = prepend_exact(reranked_points, exact, rerank_k)
            metrics.candidate_count = len(reranked_points)

        # Extract graph roots
        node_ids = self.extract_ids(reranked_points)

        # Expand graph
        graph_context = {}
        if include_graph:
            with log_stage("graph_expansion") as metrics:
                graph_context = self.expand_graph(node_ids)
                metrics.candidate_count = len(graph_context)

        return {

            "query": query,
            "vector_results": dense_points,
            "fused_results": points,
            "reranked_results": reranked_points,
            "node_ids": node_ids,
            "graph_context": graph_context
        }

if __name__=="__main__":
    r=HybridRetriever()
    r.retrieve("My bike was stolen from outside my house. What punishment can the offender face?")