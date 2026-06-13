from qdrant_client import (
    QdrantClient
)

from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)


class QdrantStore:

    def __init__(
        self,
        collection_name: str,
        host="localhost",
        port=6333
    ):

        self.collection_name = (
            collection_name
        )

        self.client = (
            QdrantClient(
                host=host,
                port=port
            )
        )

    def create_collection(
        self,
        vector_size: int
    ):

        collections = (
            self.client
            .get_collections()
        )

        existing = {
            c.name
            for c in collections.collections
        }

        if (
            self.collection_name
            not in existing
        ):

            self.client.create_collection(
                collection_name=
                    self.collection_name,

                vectors_config=
                    VectorParams(
                        size=
                            vector_size,

                        distance=
                            Distance.COSINE
                    )
            )

    def upsert(
        self,
        points
    ):

        self.client.upsert(
            collection_name=
                self.collection_name,

            points=
                points
        )

    def search(
        self,
        query_vector,
        limit=10
    ):

        return (
            self.client.query_points(
                collection_name=
                    self.collection_name,

                query=
                    query_vector,

                limit=
                    limit
            )
        )