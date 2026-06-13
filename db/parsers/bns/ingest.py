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

    def __init__(self):

        self.embedder = (
            LegalEmbedder()
        )

        self.store = (
            QdrantStore(
                collection_name="bns"
            )
        )

    def ingest(
        self,
        chunks,
        batch_size=64
    ):

        dimension = (
            self.embedder
            .model
            .get_sentence_embedding_dimension()
        )

        self.store.create_collection(
            dimension
        )

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

            for chunk, embedding in zip(
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