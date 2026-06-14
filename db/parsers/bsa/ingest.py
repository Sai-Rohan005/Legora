from __future__ import annotations

from tqdm import tqdm

from qdrant_client.models import (
    PointStruct
)

from db.parsers.bsa.embedder import (
    LegalEmbedder
)

from db.parsers.bsa.qdrant_store import (
    QdrantStore
)


class LegalIngestionPipeline:

    def __init__(
        self,
        collection_name: str
    ):

        self.embedder = (
            LegalEmbedder()
        )

        self.store = (
            QdrantStore(
                collection_name=
                    collection_name
            )
        )

    # =====================================================
    # INGEST
    # =====================================================

    def ingest(
        self,
        chunks,
        batch_size: int = 64,
        recreate_collection: bool = False
    ):

        # ==========================================
        # VECTOR SIZE
        # ==========================================

        vector_size = (
            self.embedder.dimension
        )

        # ==========================================
        # RECREATE COLLECTION
        # ==========================================

        if recreate_collection:

            self.store.delete_collection()

        # ==========================================
        # CREATE COLLECTION
        # ==========================================

        self.store.create_collection(
            vector_size
        )

        # ==========================================
        # UPSERT BATCHES
        # ==========================================

        point_id = 1

        for start in tqdm(
            range(
                0,
                len(chunks),
                batch_size
            ),
            desc="Indexing"
        ):

            batch = chunks[
                start:
                start + batch_size
            ]

            texts = [
                chunk[
                    "enriched_text"
                ]
                for chunk in batch
            ]

            embeddings = (
                self.embedder.embed(
                    texts
                )
            )

            points = []

            for (
                chunk,
                embedding
            ) in zip(
                batch,
                embeddings
            ):

                points.append(
                    PointStruct(
                        id=point_id,

                        vector=
                            embedding.tolist(),

                        payload=
                            chunk
                    )
                )

                point_id += 1

            self.store.upsert(
                points
            )

        # ==========================================
        # SUMMARY
        # ==========================================

        print()

        print(
            f"Indexed "
            f"{len(chunks)} chunks "
            f"into "
            f"{self.store.collection_name}"
        )

        print(
            f"Total points: "
            f"{self.store.count()}"
        )