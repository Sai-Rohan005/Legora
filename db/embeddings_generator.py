from sentence_transformers import SentenceTransformer
from typing import List, Dict


class LegalEmbedder:
    """
    Converts legal records into embeddings.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5"
    ):
        self.model = SentenceTransformer(
            model_name
        )

    def embed_records(
        self,
        records: List[Dict]
    ) -> List[Dict]:

        if not records:
            return []

        texts = [
            record["embedding_text"]
            for record in records
        ]

        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )

        for record, embedding in zip(
            records,
            embeddings
        ):
            record["embedding"] = (
                embedding.tolist()
            )

        return records