# app_context.py

from sentence_transformers import SentenceTransformer
from db.vector_store import QdrantIngestor
from db.graph_db import LegalGraphDB


class AppContext:
    _embedder = None
    _qdrant = None
    _graph = None

    @classmethod
    def get_embedder(cls, model_name="BAAI/bge-large-en-v1.5"):
        if cls._embedder is None:
            print("🔄 Loading embedder once...")
            cls._embedder = SentenceTransformer(model_name, device="mps")
        return cls._embedder

    @classmethod
    def get_qdrant(cls):
        if cls._qdrant is None:
            print("🔄 Connecting Qdrant...")
            cls._qdrant = QdrantIngestor()
        return cls._qdrant

    @classmethod
    def get_graph(cls):
        if cls._graph is None:
            print("🔄 Connecting Neo4j...")
            cls._graph = LegalGraphDB(
                uri="bolt://localhost:7687",
                user="neo4j",
                password="test12345"
            )
        return cls._graph