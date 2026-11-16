from __future__ import annotations

import logging

from sentence_transformers import (
    SentenceTransformer
)

logger = logging.getLogger(__name__)


class LegalEmbedder:

    def __init__(
        self,
        model_name: str =
        "BAAI/bge-large-en-v1.5"
    ):

        logger.info("Loading embedding model: %s", model_name)

        self.model = (
            SentenceTransformer(
                model_name
            )
        )

    # =====================================================
    # DOCUMENT EMBEDDINGS
    # =====================================================

    def embed(
        self,
        texts: list[str]
    ):

        return self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=16,
            show_progress_bar=True
        )

    # =====================================================
    # QUERY EMBEDDING
    # =====================================================

    def embed_query(
        self,
        query: str
    ):

        query = (
            "Represent this sentence "
            "for searching relevant "
            f"passages: {query}"
        )

        return self.model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

    # =====================================================
    # VECTOR SIZE
    # =====================================================

    def vector_size(
        self
    ) -> int:

        return (
            self.model
            .get_sentence_embedding_dimension()
        )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    embedder = (
        LegalEmbedder()
    )

    texts = [
        "Section 52. Facts of which Court shall take judicial notice.",
        "Article 21. Protection of life and personal liberty."
    ]

    vectors = (
        embedder.embed(
            texts
        )
    )

    logger.debug('%s %s', "Vectors:", len(vectors))

    logger.debug('%s %s', "Dimension:", len(vectors[0]))

    query_vector = (
        embedder.embed_query(
            "facts judicially noticed by court"
        )
    )

    logger.debug('%s %s', "Query Dimension:", len(query_vector))

    logger.debug('%s %s', "Model Dimension:", embedder.vector_size())