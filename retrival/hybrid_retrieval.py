from __future__ import annotations

from db.embedder import LegalEmbedder
from db.vector_store import QdrantStore
from db.neo4j_store import Neo4jStore
from retrival.cross_encoder import LegalReranker


class HybridRetriever:

    def __init__(self):

        self.embedder = LegalEmbedder()

        self.vector_db = QdrantStore(
            collection_name="legal_rag"
        )

        self.graph = Neo4jStore(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="test12345"
        )

    # =====================================================
    # VECTOR SEARCH
    # =====================================================

    def vector_search(
        self,
        query: str,
        k: int = 10
    ):

        query_vector = (
            self.embedder.embed_query(
                query
            )
        )

        result = (
            self.vector_db.search(
                query_vector=query_vector,
                limit=k
            )
        )

        return result.points

    # =====================================================
    # NODE IDS
    # =====================================================

    def extract_ids(
        self,
        points
    ):

        ids = set()

        for point in points:

            payload = point.payload

            chunk_id = payload.get(
                "chunk_id"
            )

            if not chunk_id:
                continue

            # BSA-52(1)(a)
            # BNS-103
            # CONST-21

            root_id = (
                chunk_id
                .split("-EXPL")[0]
                .split("-ILL")[0]
            )

            ids.add(root_id)

        return list(ids)

    # =====================================================
    # ANCESTORS
    # =====================================================

    def get_ancestors(
        self,
        node_id: str
    ):

        query = """
        MATCH p=(n {id:$id})
        -[:BELONGS_TO*0..10]->
        (parent)

        RETURN p
        """

        return self.graph.run_query(
            query,
            {"id": node_id}
        )

    # =====================================================
    # CHILDREN
    # =====================================================

    def get_children(
        self,
        node_id: str
    ):

        query = """
        MATCH p=(n {id:$id})
        -[:HAS_ARTICLE|
          HAS_CHAPTER|
          HAS_SECTION|
          HAS_CLAUSE|
          HAS_SUBCLAUSE|
          HAS_ROMANCLAUSE|
          HAS_PROVISO|
          HAS_EXPLANATION|
          HAS_ILLUSTRATION*0..3]->
        (child)

        RETURN p
        """

        return self.graph.run_query(
            query,
            {"id": node_id}
        )

    # =====================================================
    # REFERENCES
    # =====================================================

    def get_references(
        self,
        node_id: str
    ):

        query = """
        MATCH (n {id:$id})
        -[:REFERENCES]->
        (ref)

        RETURN ref
        """

        return self.graph.run_query(
            query,
            {"id": node_id}
        )

    # =====================================================
    # GRAPH EXPANSION
    # =====================================================

    def expand_graph(
        self,
        node_ids
    ):

        graph_context = {}

        for node_id in node_ids:

            graph_context[node_id] = {

                "ancestors":
                    self.get_ancestors(
                        node_id
                    ),

                "children":
                    self.get_children(
                        node_id
                    ),

                "references":
                    self.get_references(
                        node_id
                    )
            }

        return graph_context

    # =====================================================
    # HYBRID RETRIEVE
    # =====================================================

    def retrieve(
        self,
        query: str,
        vector_k: int = 30,
        rerank_k: int = 5
    ):

        # -----------------------------------------
        # Vector Search
        # -----------------------------------------

        points = (
            self.vector_search(
                query,
                vector_k
            )
        )

        # -----------------------------------------
        # Rerank
        # -----------------------------------------

        reranked_points = (
            self.reranker.rerank(
                query=query,
                points=points,
                top_k=rerank_k
            )
        )

        # -----------------------------------------
        # Node IDs
        # -----------------------------------------

        node_ids = (
            self.extract_ids(
                reranked_points
            )
        )

        # -----------------------------------------
        # Graph Expansion
        # -----------------------------------------

        graph_context = (
            self.expand_graph(
                node_ids
            )
        )

        # -----------------------------------------
        # Return
        # -----------------------------------------

        return {

            "query":
                query,

            "vector_results":
                points,

            "reranked_results":
                reranked_points,

            "node_ids":
                node_ids,

            "graph_context":
                graph_context
        }