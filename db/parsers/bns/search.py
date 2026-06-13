from sentence_transformers import (
    SentenceTransformer
)

from qdrant_client import (
    QdrantClient
)


class BNSRetriever:

    def __init__(
        self,
        collection_name="bns",
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

        hits = (
            self.client.query_points(
                collection_name=
                    self.collection_name,

                query=
                    query_vector,

                limit=
                    limit
            )
        )

        return hits
    

if __name__=="__main__":
    query = "punishment for trafficking of person"
    
    bns_search=BNSRetriever()
    print(bns_search.search(query))
