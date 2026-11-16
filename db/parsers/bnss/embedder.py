from __future__ import annotations

from typing import List

from sentence_transformers import (
    SentenceTransformer
)


class LegalEmbedder:

    def __init__(
        self,
        model_name: str =
        "BAAI/bge-large-en-v1.5"
    ):

        self.model_name = model_name

        self.model = (
            SentenceTransformer(
                model_name
            )
        )

        self.vector_size = (
            self.model
            .get_sentence_embedding_dimension()
        )

    # =====================================
    # EMBED DOCUMENTS
    # =====================================

    def embed(
        self,
        texts: List[str]
    ):

        return self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False
        )

    # =====================================
    # EMBED QUERY
    # =====================================

    def embed_query(
        self,
        query: str
    ):

        return (
            self.model.encode(
                query,
                normalize_embeddings=True,
                convert_to_numpy=True
            )
        )

    # =====================================
    # EMBED SINGLE TEXT
    # =====================================

    def embed_text(
        self,
        text: str
    ):

        return (
            self.model.encode(
                text,
                normalize_embeddings=True,
                convert_to_numpy=True
            )
        )

    # =====================================
    # INFO
    # =====================================

    def info(
        self
    ):

        return {
            "model":
                self.model_name,

            "vector_size":
                self.vector_size
        }