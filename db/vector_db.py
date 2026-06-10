from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import hashlib


class QdrantIngestor:

    def __init__(
        self,
        collection_name: str = "legal_constitution",
        vector_size: int = 1024
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
    # UPSERT (IDEMPOTENT)
    # -----------------------------
    def upsert_chunks(self, records, embeddings):

        points = []

        for record, vector in zip(records, embeddings):

            points.append(
                PointStruct(
                    id=record["id"],

                    vector=vector.tolist(),

                    payload={
                        **record["metadata"],

                        "chunk_type":
                            record["chunk_type"],

                        "embedding_text":
                            record["embedding_text"]
                    }
                )
            )

        BATCH_SIZE = 100

        for i in range(0, len(points), BATCH_SIZE):

            batch = points[i:i+BATCH_SIZE]

            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )

            print(
                f"Uploaded {min(i+BATCH_SIZE, len(points))}/{len(points)}"
            )

        print(
            f"Inserted/Updated {len(points)} records into Qdrant"
        )

    def search(
        self,
        query_vector,
        limit=5
    ):

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector.tolist(),
            limit=limit,
            with_payload=True,
            with_vectors=False
        )

        return results.points