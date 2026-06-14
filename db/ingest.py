from __future__ import annotations

from db.embedder import LegalEmbedder
from db.vector_store import QdrantStore


class LegalIngestionPipeline:

    def __init__(
        self,
        collection_name: str = "legal_rag"
    ):

        self.embedder = LegalEmbedder()

        self.store = QdrantStore(
            collection_name=
                collection_name
        )

    # =====================================================
    # INGEST
    # =====================================================

    def ingest(
        self,
        chunks: list[dict],
        recreate_collection: bool = False
    ):

        if not chunks:

            print(
                "No chunks found."
            )

            return

        print(
            f"\nChunks: {len(chunks)}"
        )

        texts = [
            chunk[
                "enriched_text"
            ]
            for chunk in chunks
        ]

        print(
            "Generating embeddings..."
        )

        embeddings = (
            self.embedder.embed(
                texts
            )
        )

        vector_size = len(
            embeddings[0]
        )

        print(
            f"Vector Size: "
            f"{vector_size}"
        )

        if recreate_collection:

            self.store.recreate_collection(
                vector_size
            )

        else:

            self.store.create_collection(
                vector_size
            )

        points = []

        for idx, (
            chunk,
            vector
        ) in enumerate(
            zip(
                chunks,
                embeddings
            ),
            start=1
        ):

            points.append(
                {
                    "id":
                        idx,

                    "vector":
                        vector.tolist(),

                    "payload":
                        chunk
                }
            )

        print(
            f"Uploading "
            f"{len(points)} points..."
        )

        self.store.upsert_points(
            points
        )

        print(
            "\nIngestion Complete."
        )