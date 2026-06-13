from __future__ import annotations

from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient

from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
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

    # =====================================
    # COLLECTION
    # =====================================

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

    def delete_collection(
        self
    ):

        if self.collection_exists():

            self.client.delete_collection(
                self.collection_name
            )

    # =====================================
    # INSERT
    # =====================================

    def upsert(
        self,
        points: List[PointStruct]
    ):

        self.client.upsert(
            collection_name=
                self.collection_name,

            points=
                points
        )

    # =====================================
    # SEARCH
    # =====================================

    def search(
        self,
        query_vector,
        limit: int = 10,
        level: Optional[str] = None
    ):

        query_filter = None

        if level:

            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="level",
                        match=
                            MatchValue(
                                value=level
                            )
                    )
                ]
            )

        result = (
            self.client.query_points(
                collection_name=
                    self.collection_name,

                query=
                    query_vector,

                query_filter=
                    query_filter,

                limit=
                    limit
            )
        )

        return result.points

    # =====================================
    # RETRIEVE BY ID
    # =====================================

    def retrieve(
        self,
        ids: List[int]
    ):

        return (
            self.client.retrieve(
                collection_name=
                    self.collection_name,

                ids=ids
            )
        )

    # =====================================
    # SCROLL
    # =====================================

    def scroll(
        self,
        limit: int = 100
    ):

        records, _ = (
            self.client.scroll(
                collection_name=
                    self.collection_name,

                limit=
                    limit,

                with_payload=True
            )
        )

        return records

    # =====================================
    # COUNT
    # =====================================

    def count(
        self
    ) -> int:

        result = (
            self.client.count(
                collection_name=
                    self.collection_name
            )
        )

        return result.count

    # =====================================
    # GET SECTION
    # =====================================

    def get_section(
        self,
        section_no: str
    ):

        records, _ = (
            self.client.scroll(
                collection_name=
                    self.collection_name,

                scroll_filter=
                    Filter(
                        must=[
                            FieldCondition(
                                key="section_no",
                                match=
                                    MatchValue(
                                        value=section_no
                                    )
                            )
                        ]
                    ),

                limit=100
            )
        )

        return records

    # =====================================
    # GET CHUNK
    # =====================================

    def get_chunk(
        self,
        chunk_id: str
    ):

        records, _ = (
            self.client.scroll(
                collection_name=
                    self.collection_name,

                scroll_filter=
                    Filter(
                        must=[
                            FieldCondition(
                                key="chunk_id",
                                match=
                                    MatchValue(
                                        value=chunk_id
                                    )
                            )
                        ]
                    ),

                limit=1
            )
        )

        return (
            records[0]
            if records
            else None
        )