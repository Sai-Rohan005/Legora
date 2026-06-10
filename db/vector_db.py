from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class QdrantIngestor:

    def __init__(
        self,
        collection_name: str = "legal_chunks",
        vector_size: int = 1024
    ):

        self.client = QdrantClient(
            host="localhost",
            port=6333
        )

        self.collection_name = collection_name
        self.vector_size = vector_size

        self._create_collection()

    # ---------------------------------------
    # CREATE COLLECTION (IDEMPOTENT)
    # ---------------------------------------
    def _create_collection(self):

        collections = self.client.get_collections().collections
        existing = {c.name for c in collections}

        if self.collection_name not in existing:

            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )

    # ---------------------------------------
    # UPSERT CHUNKS (RECORD-BASED INPUT)
    # ---------------------------------------
    def upsert_chunks(self, records):

        points = []

        for record in records:

            vector = record.get("embedding")

            # skip bad records
            if vector is None:
                continue

            # convert numpy → list if needed
            if hasattr(vector, "tolist"):
                vector = vector.tolist()

            points.append(
                PointStruct(
                    id=record["id"],

                    vector=vector,

                    payload={
                        "document_type": record.get("document_type"),
                        "chunk_type": record.get("chunk_type"),
                        "embedding_text": record.get("embedding_text"),
                        **record.get("metadata", {})
                    }
                )
            )

        # -----------------------
        # BATCH UPLOAD
        # -----------------------
        BATCH_SIZE = 100

        for i in range(0, len(points), BATCH_SIZE):

            batch = points[i:i + BATCH_SIZE]

            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )

            print(
                f"Uploaded {min(i + BATCH_SIZE, len(points))}"
                f"/{len(points)}"
            )

        print(f"Inserted {len(points)} records into Qdrant")

    # ---------------------------------------
    # SEARCH
    # ---------------------------------------
    def search(self, query_vector, limit=5):

        if hasattr(query_vector, "tolist"):
            query_vector = query_vector.tolist()

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )

        return results.points