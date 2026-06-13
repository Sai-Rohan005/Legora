from __future__ import annotations

from tqdm import tqdm

from qdrant_client.models import (
    PointStruct
)

from embedder_temp import (
    LegalEmbedder
)

from qdrant_store import (
    QdrantStore
)


class LegalIngestionPipeline:

    def __init__(
        self,
        collection_name: str = "bnss"
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

    # =====================================
    # INGEST
    # =====================================

    def ingest(
        self,
        chunks,
        batch_size: int = 64,
        recreate_collection: bool = False
    ):

        vector_size = (
            self.embedder.vector_size
        )

        if recreate_collection:

            try:
                self.store.delete_collection()
            except Exception:
                pass

        self.store.create_collection(
            vector_size
        )

        point_id = 1

        for start in tqdm(
            range(
                0,
                len(chunks),
                batch_size
            ),
            desc="Embedding"
        ):

            batch = chunks[
                start:
                start + batch_size
            ]

            texts = [
                chunk.get(
                    "enriched_text",
                    chunk["text"]
                )
                for chunk in batch
            ]

            embeddings = (
                self.embedder.embed(
                    texts
                )
            )

            points = []

            for chunk, vector in zip(
                batch,
                embeddings
            ):

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=
                            vector.tolist(),
                        payload=
                            chunk
                    )
                )

                point_id += 1

            self.store.upsert(
                points
            )

        print(
            f"\nIndexed "
            f"{len(chunks)} chunks "
            f"into "
            f"{self.store.collection_name}"
        )