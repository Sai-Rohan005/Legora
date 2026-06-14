from __future__ import annotations

from sentence_transformers import (
    SentenceTransformer
)

import numpy as np


class LegalEmbedder:

    def __init__(
        self,
        model_name: str =
        "BAAI/bge-large-en-v1.5"
    ):

        self.model = (
            SentenceTransformer(
                model_name
            )
        )

    # ==========================================
    # SINGLE TEXT
    # ==========================================

    def embed_query(
        self,
        text: str
    ) -> np.ndarray:

        return self.model.encode(
            text,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

    # ==========================================
    # BATCH TEXTS
    # ==========================================

    def embed(
        self,
        texts: list[str]
    ) -> np.ndarray:

        return self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False
        )

    # ==========================================
    # VECTOR DIMENSION
    # ==========================================

    @property
    def dimension(
        self
    ) -> int:

        return (
            self.model
            .get_sentence_embedding_dimension()
        )


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    embedder = LegalEmbedder()

    vec = embedder.embed_query(
        "punishment for trafficking"
    )

    print(
        "Dimension:",
        len(vec)
    )

    print(
        vec[:10]
    )