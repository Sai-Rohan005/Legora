from embedder_temp import LegalEmbedder
from qdrant_store import QdrantStore


class BNSSRetriever:

    def __init__(
        self,
        collection_name="bnss"
    ):

        self.embedder = (
            LegalEmbedder()
        )

        self.store = (
            QdrantStore(
                collection_name=
                    collection_name
            )
        )

    def search(
        self,
        query: str,
        limit: int = 10,
        level: str | None = None
    ):

        query_vector = (
            self.embedder.embed(
                [query]
            )[0]
        )

        return self.store.search(
            query_vector=
                query_vector.tolist(),

            limit=
                limit,

            level=
                level
        )
    

if __name__ == "__main__":

    query = (
        "security for good behaviour from habitual offenders"
    )

    retriever = (
        BNSSRetriever(
            collection_name="bnss"
        )
    )

    results = retriever.search(
        query,
        limit=5
    )

    for i, point in enumerate(
        results,
        start=1
    ):

        payload = point.payload

        print("\n" + "=" * 80)

        print(
            f"Rank      : {i}"
        )

        print(
            f"Score     : {point.score:.4f}"
        )

        print(
            f"Chunk ID  : {payload['chunk_id']}"
        )

        print(
            f"Section   : {payload['section_no']}"
        )

        print(
            f"Level     : {payload['level']}"
        )

        print(
            f"\n{payload['text']}"
        )