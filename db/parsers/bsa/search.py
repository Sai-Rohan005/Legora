from __future__ import annotations

from sentence_transformers import (
    SentenceTransformer
)

from qdrant_client import (
    QdrantClient
)


class LegalRetriever:

    def __init__(
        self,
        collection_name="bsa",
        model_name="BAAI/bge-large-en-v1.5"
    ):

        self.collection_name = (
            collection_name
        )

        self.client = (
            QdrantClient(
                host="localhost",
                port=6333
            )
        )

        self.model = (
            SentenceTransformer(
                model_name
            )
        )

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query: str,
        limit: int = 10
    ):

        query_vector = (
            self.model.encode(
                query,
                normalize_embeddings=True
            ).tolist()
        )

        result = (
            self.client.query_points(
                collection_name=
                    self.collection_name,

                query=
                    query_vector,

                limit=
                    limit
            )
        )

        return result.points

if __name__=="__main__":
    query="facts judicially noticed by court"
    r=LegalRetriever()
    print(r.search(query))