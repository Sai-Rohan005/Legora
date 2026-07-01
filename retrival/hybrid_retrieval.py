from __future__ import annotations

from db.embedder import LegalEmbedder
from db.vector_store import QdrantStore
from db.neo4j_store import Neo4jStore
from retrival.cross_encoder import LegalReranker
from LegalRag.query_analyser import Analyser

class HybridRetriever:

    def __init__(self):

        self.embedder = LegalEmbedder()
        self.reranker = LegalReranker()
        self.analyser=Analyser()

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

    def extract_ids(self, points):

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

            root_id = chunk_id.split("(")[0].split("-EXPL")[0].split("-ILL")[0]

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
        MATCH p = (n)-[:BELONGS_TO*0..10]->(child)
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

        act = analysis.acts[0].lower()

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

    def retrieve(self, query: str, vector_k: int = 10, rerank_k: int = 5):

        analysis = self.analyser.analyze_query(query)
        # print(analysis)

        queries = self.build_retrieval_queries(
            analysis
        )
        # for q in queries:
        #     print(q)

        points = []

        document_filter = self.get_document_filter(
            analysis
        )

        print(
            f"\nDocument Filter: "
            f"{document_filter}"
        )

        for q in queries:

            results = self.vector_search_filtered(
                query=q,
                document=document_filter,
                k=vector_k
            )

            points.extend(results)
        
        points=self.dedupe_points(points)
        print("\n" + "=" * 80)
        print("TOP RESULTS BEFORE RERANK")
        print("=" * 80)

        sorted_points = sorted(
            points,
            key=lambda x: x.score,
            reverse=True
        )

        for idx, point in enumerate(
            sorted_points[:20],
            start=1
        ):

            print(
                f"{idx}. "
                f"{point.payload.get('chunk_id')} "
                f"| {point.score:.4f}"
            )

        # Rerank
        reranked_points = self.reranker.rerank(
            query=query,
            points=points,
            top_k=rerank_k,
            analysis=analysis
        )

        # Extract graph roots
        node_ids = self.extract_ids(reranked_points)

        # Expand graph
        graph_context = self.expand_graph(node_ids)

        return {

            "query": query,
            "vector_results": points,
            "reranked_results": reranked_points,
            "node_ids": node_ids,
            "graph_context": graph_context
        }

if __name__=="__main__":
    r=HybridRetriever()
    r.retrieve("My bike was stolen from outside my house. What punishment can the offender face?")