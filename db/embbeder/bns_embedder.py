from __future__ import annotations

from typing import List

from tqdm import tqdm

from sentence_transformers import (
    SentenceTransformer
)

from qdrant_client import QdrantClient

from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct
)


class QdrantEmbeddingGenerator:

    def __init__(
        self,
        collection_name: str = "bns",
        model_name: str = "BAAI/bge-large-en-v1.5",
        host: str = "localhost",
        port: int = 6333
    ):

        self.collection_name = (
            collection_name
        )

        self.model = (
            SentenceTransformer(
                model_name
            )
        )

        self.client = (
            QdrantClient(
                host=host,
                port=port
            )
        )

    # =====================================
    # CREATE COLLECTION
    # =====================================

    def create_collection(self):

        dimension = (
            self.model
            .get_sentence_embedding_dimension()
        )

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
                        size=dimension,
                        distance=
                            Distance.COSINE
                    )
            )

            print(
                f"Created collection "
                f"{self.collection_name}"
            )

    # =====================================
    # BUILD TEXT
    # =====================================

    def build_text(
        self,
        chunk: dict
    ) -> str:

        return chunk.get(
            "enriched_text",
            chunk["text"]
        )

    # =====================================
    # INGEST
    # =====================================

    def ingest_chunks(
        self,
        chunks: List[dict],
        batch_size: int = 64
    ):

        self.create_collection()

        point_id = 1

        for start in tqdm(
            range(
                0,
                len(chunks),
                batch_size
            )
        ):

            batch = chunks[
                start:
                start + batch_size
            ]

            texts = [
                self.build_text(
                    chunk
                )
                for chunk in batch
            ]

            embeddings = (
                self.model.encode(
                    texts,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False
                )
            )

            points = []

            for chunk, embedding in zip(
                batch,
                embeddings
            ):

                payload = {

                    "chunk_id":
                        chunk.get(
                            "chunk_id"
                        ),

                    "level":
                        chunk.get(
                            "level"
                        ),

                    "chapter_no":
                        chunk.get(
                            "chapter_no"
                        ),

                    "section_no":
                        chunk.get(
                            "section_no"
                        ),

                    "clause_no":
                        chunk.get(
                            "clause_no"
                        ),

                    "sub_clause_no":
                        chunk.get(
                            "sub_clause_no"
                        ),

                    "roman_no":
                        chunk.get(
                            "roman_no"
                        ),

                    "title":
                        chunk.get(
                            "title"
                        ),

                    "text":
                        chunk.get(
                            "text"
                        ),

                    "parent_id":
                        chunk.get(
                            "parent_id"
                        )
                }

                points.append(
                    PointStruct(
                        id=point_id,
                        vector=
                            embedding.tolist(),
                        payload=
                            payload
                    )
                )

                point_id += 1

            self.client.upsert(
                collection_name=
                    self.collection_name,

                points=
                    points
            )

        print(
            f"Ingested "
            f"{len(chunks)} chunks"
        )