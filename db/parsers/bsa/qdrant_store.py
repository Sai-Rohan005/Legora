from __future__ import annotations

from typing import List

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
        host: str = "localhost",
        port: int = 6333
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

    # =====================================================
    # COLLECTION EXISTS
    # =====================================================

    def collection_exists(
        self
    ) -> bool:

        collections = (
            self.client
            .get_collections()
        )

        existing = {
            c.name
            for c in collections.collections
        }

        return (
            self.collection_name
            in existing
        )

    # =====================================================
    # CREATE COLLECTION
    # =====================================================

    def create_collection(
        self,
        vector_size: int
    ):

        if self.collection_exists():

            print(
                f"Collection "
                f"{self.collection_name} "
                f"already exists."
            )

            return

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

        print(
            f"Created collection "
            f"{self.collection_name}"
        )

    # =====================================================
    # DELETE COLLECTION
    # =====================================================

    def delete_collection(
        self
    ):

        if not self.collection_exists():

            return

        self.client.delete_collection(
            collection_name=
                self.collection_name
        )

        print(
            f"Deleted collection "
            f"{self.collection_name}"
        )

    # =====================================================
    # UPSERT
    # =====================================================

    def upsert(
        self,
        points: List[PointStruct]
    ):

        self.client.upsert(
            collection_name=
                self.collection_name,

            points=
                points,

            wait=True
        )

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query_vector,
        limit: int = 10
    ):

        result = (
            self.client.query_points(
                collection_name=
                    self.collection_name,

                query=
                    query_vector,

                limit=
                    limit
            )
        )

        return result.points

    # =====================================================
    # COUNT
    # =====================================================

    def count(
        self
    ) -> int:

        return (
            self.client.count(
                collection_name=
                    self.collection_name,
                exact=True
            ).count
        )

    # =====================================================
    # INFO
    # =====================================================

    def info(
        self
    ):

        return (
            self.client.get_collection(
                self.collection_name
            )
        )


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    store = QdrantStore(
        collection_name="bsa"
    )

    print(
        "Exists:",
        store.collection_exists()
    )

    if store.collection_exists():

        print(
            "Points:",
            store.count()
        )