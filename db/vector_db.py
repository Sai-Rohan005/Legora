from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib


class QdrantIngestor:

    def __init__(
        self,
        collection_name: str = "legal_constitution",
        vector_size: int = 384
    ):

        self.client = QdrantClient(host="localhost", port=6333)
        self.collection_name = collection_name
        self.vector_size = vector_size

        self._create_collection()

    def _create_collection(self):
        collections = self.client.get_collections().collections
        existing = [c.name for c in collections]

        if self.collection_name not in existing:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )

    # -----------------------------
    # STABLE ID GENERATOR
    # -----------------------------
    def _make_id(self, chunk: dict) -> str:

        raw = (
        str(chunk.part_no or "") +
        str(chunk.article_no or "") +
        str(chunk.clause_no or "") +
        str(hash(chunk.text))
    )

        return hashlib.md5(raw.encode()).hexdigest()

    # -----------------------------
    # UPSERT (IDEMPOTENT)
    # -----------------------------
    def upsert_chunks(self, chunks, embeddings):

        points = []

        for chunk, vector in zip(chunks, embeddings):

            point_id = self._make_id(chunk)

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vector.tolist(),
                    payload = {
                        "text": chunk.text,
                        "part": chunk.part_no,
                        "part_title": chunk.part_title,
                        "article": chunk.article_no,
                        "article_title": chunk.article_title,
                        "clause": chunk.clause_no,
                        "sub_clause": chunk.sub_clause_no,
                    }
                )
            )

        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        print(f"Inserted/Updated {len(points)} chunks into Qdrant")