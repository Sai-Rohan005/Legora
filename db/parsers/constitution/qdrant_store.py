from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)


class QdrantStore:

    def __init__(
        self,
        host="localhost",
        port=6333,
        collection_name="constitution"
    ):

        self.collection_name = (
            collection_name
        )

        self.client = QdrantClient(
            host=host,
            port=port
        )

    # =====================================================
    # CREATE COLLECTION
    # =====================================================

    def create_collection(
        self,
        vector_size: int
    ):

        collections = (
            self.client.get_collections()
        )

        existing = {
            c.name
            for c in collections.collections
        }

        if (
            self.collection_name
            in existing
        ):
            print(
                "Collection exists"
            )
            return

        self.client.create_collection(
            collection_name=
                self.collection_name,

            vectors_config=
                VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
        )

        print(
            "Collection created"
        )

    # =====================================================
    # INSERT
    # =====================================================

    def insert_chunks(
        self,
        chunks,
        embeddings,
        batch_size=100
    ):

        total = len(chunks)

        for start in range(
            0,
            total,
            batch_size
        ):

            end = min(
                start + batch_size,
                total
            )

            points = []

            for idx in range(
                start,
                end
            ):

                chunk = chunks[idx]

                embedding = embeddings[idx]

                payload = {
                    "chunk_id":
                        chunk.chunk_id,

                    "chunk_type":
                        chunk.chunk_type,

                    "text":
                        chunk.text,

                    "references":
                        chunk.references,

                    **chunk.metadata
                }

                points.append(
                    PointStruct(
                        id=idx,

                        vector=
                            embedding.tolist(),

                        payload=
                            payload
                    )
                )

            self.client.upsert(
                collection_name=
                    self.collection_name,

                points=
                    points
            )

            print(
                f"Inserted "
                f"{end}/{total}"
            )