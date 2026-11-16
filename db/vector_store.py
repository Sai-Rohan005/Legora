from __future__ import annotations

import logging

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    VectorParams,
    PointStruct,
    SearchParams
)
from legora.config import EvaluationSettings, Settings, get_settings

logger = logging.getLogger(__name__)



class QdrantStore:

    def __init__(
        self,
        collection_name: str = "legal_rag",
        settings: Settings | EvaluationSettings | None = None,
        exact_search: bool = False
    ) -> None:
        """Use shared settings, allowing evaluation without unrelated services."""
        config = settings or get_settings()
        if not config.qdrant_url or not config.qdrant_url.strip():
            raise ValueError("QDRANT_URL is required")
        self.exact_search = exact_search
        self.collection_name = collection_name
        self.client = QdrantClient(
            url=config.qdrant_url,
            api_key=config.qdrant_api_key.get_secret_value() if config.qdrant_api_key else None,
            timeout=config.external_timeout_seconds,
            check_compatibility=False
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
        batch_size: int = 8
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

            logger.debug("Uploaded %s/%s", min(end, total), total)

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
            **({"search_params": SearchParams(exact=True)} if self.exact_search else {}),
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

            **({"search_params": SearchParams(exact=True)} if self.exact_search else {}),
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