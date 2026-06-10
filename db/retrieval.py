from sentence_transformers import SentenceTransformer


class LegalRetriever:

    def __init__(
        self,
        qdrant_db,
        model_name="BAAI/bge-large-en-v1.5"
    ):

        self.qdrant = qdrant_db

        self.model = SentenceTransformer(
            model_name
        )

    def embed_query(
        self,
        query: str
    ):

        return self.model.encode(
            query,
            normalize_embeddings=True
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5
    ):

        query_vector = self.embed_query(
            query
        )

        results = self.qdrant.search(
            query_vector=query_vector,
            limit=top_k
        )

        retrieved = []

        for result in results:
            if result.score >= 0.75:
                retrieved.append(
                    {
                        "score": result.score,
                        "payload": result.payload
                    }
                )

        return retrieved