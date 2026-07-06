from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    VectorParams,
    PointStruct
)
import os



class QdrantStore:

    def __init__(
        self,
        collection_name: str = "legal_rag",
        host: str = "localhost",
        port: int = 6333
    ):
        qdrant_url = os.getenv("QDRANT_URL")
        qdrant_api_key = os.getenv("QDRANT_API_KEY")


        self.collection_name = (
            collection_name
        )

        if qdrant_url:
            self.client = QdrantClient(
                url=qdrant_url,
                api_key=qdrant_api_key,
                check_compatibility=False
            )
        else:
            self.client = QdrantClient(
                host="localhost",
                port=6333
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
            .collections
        )

        return any(
            c.name ==
            self.collection_name
            for c in collections
        )

    # =====================================================
    # CREATE COLLECTION
    # =====================================================

    def create_collection(
        self,
        vector_size: int
    ):

        if self.collection_exists():

            return

        self.client.create_collection(
            collection_name=
                self.collection_name,

            vectors_config=
                VectorParams(
                    size=vector_size,
                    distance=
                        Distance.COSINE
                )
        )

    # =====================================================
    # RECREATE COLLECTION
    # =====================================================

    def recreate_collection(
        self,
        vector_size: int
    ):

        if self.collection_exists():

            self.client.delete_collection(
                self.collection_name
            )

        self.client.create_collection(
            collection_name=
                self.collection_name,

            vectors_config=
                VectorParams(
                    size=vector_size,
                    distance=
                        Distance.COSINE
                )
        )

    # =====================================================
    # UPSERT
    # =====================================================

    def upsert_points(
        self,
        points: list[dict],
        batch_size: int = 500
    ):

        total = len(points)

        for start in range(
            0,
            total,
            batch_size
        ):

            end = start + batch_size

            batch = points[start:end]

            qdrant_points = []

            for point in batch:

                qdrant_points.append(
                    PointStruct(
                        id=point["id"],
                        vector=point["vector"],
                        payload=point["payload"]
                    )
                )

            self.client.upsert(
                collection_name=
                    self.collection_name,

                points=
                    qdrant_points,

                wait=True
            )

            print(
                f"Uploaded "
                f"{min(end,total)}"
                f"/{total}"
            )

    def search_with_filter(
        self,
        query_vector,
        document: str = None,
        limit: int = 10
    ):

        q_filter = None

        if document:

            q_filter = Filter(
                must=[
                    FieldCondition(
                        key="document",
                        match=MatchValue(
                            value=document
                        )
                    )
                ]
            )

        return self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=q_filter,
            limit=limit
        )

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query_vector,
        limit: int = 10
    ):

        return self.client.query_points(
            collection_name=
                self.collection_name,

            query=
                query_vector,

            limit=
                limit
        )

    # =====================================================
    # COUNT
    # =====================================================

    def count(
        self
    ):

        return self.client.count(
            collection_name=
                self.collection_name
        ).count