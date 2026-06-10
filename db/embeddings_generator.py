from sentence_transformers import SentenceTransformer
from typing import List, Dict


class LegalEmbedder:
    """
    Converts legal chunks into embeddings using SentenceTransformer
    """

    def __init__(self, model_name: str = "BAAI/bge-large-en-v1.5"):
        self.model = SentenceTransformer(model_name)

    def embed_texts(self, texts: List[str]):

        # Normalize input
        texts = [t.strip() for t in texts if t and t.strip()]

        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True  # IMPORTANT for cosine similarity
        )

        return embeddings