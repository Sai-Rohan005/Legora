from __future__ import annotations

import re

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Filter,
    FieldCondition,
    MatchValue
)


class ConstitutionSearch:

    def __init__(
        self,
        collection_name="constitution",
        qdrant_url="http://localhost:6333",
        api_key=None
    ):

        self.collection_name = (
            collection_name
        )

        self.client = QdrantClient(
            url=qdrant_url,
            api_key=api_key
        )

        print(
            f"Connected to: {qdrant_url}"
        )

        collections = (
            self.client.get_collections()
        )

        print("\nAvailable Collections:")

        for c in collections.collections:
            print("-", c.name)

        self.embedding_model = (
            SentenceTransformer(
                "BAAI/bge-large-en-v1.5"
            )
        )

    # =====================================================
    # ARTICLE ROUTER
    # =====================================================

    def extract_article_number(
        self,
        query: str
    ):

        match = re.search(
            r"article\s+(\d+[A-Z]*)",
            query,
            re.I
        )

        if match:
            return match.group(1)

        return None

    # =====================================================
    # ARTICLE LOOKUP
    # =====================================================

    def search_article(
        self,
        article_no: str
    ):

        records, _ = self.client.scroll(
            collection_name=
                self.collection_name,

            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="article_no",
                        match=MatchValue(
                            value=article_no
                        )
                    ),
                    FieldCondition(
                        key="chunk_type",
                        match=MatchValue(
                            value="article"
                        )
                    )
                ]
            ),

            limit=1,

            with_payload=True
        )

        return records

    # =====================================================
    # SEMANTIC SEARCH
    # =====================================================

    def semantic_search(
        self,
        query: str,
        top_k: int = 5
    ):

        query_embedding = (
            self.embedding_model.encode(
                query,
                normalize_embeddings=True
            )
        )

        result = self.client.query_points(
            collection_name=
                self.collection_name,

            query=
                query_embedding.tolist(),

            limit=
                top_k
        )

        return result.points

    # =====================================================
    # MAIN SEARCH
    # =====================================================

    def search(
        self,
        query: str,
        top_k: int = 5
    ):

        article_no = (
            self.extract_article_number(
                query
            )
        )

        if article_no:

            print(
                f"\nExact Article Lookup: "
                f"{article_no}"
            )

            return self.search_article(
                article_no
            )

        print(
            "\nSemantic Search"
        )

        return self.semantic_search(
            query,
            top_k
        )

    # =====================================================
    # PRINT RESULTS
    # =====================================================

    def print_results(
        self,
        results
    ):

        if not results:

            print(
                "No results found."
            )

            return

        for idx, result in enumerate(
            results,
            start=1
        ):

            # scroll result
            if hasattr(
                result,
                "payload"
            ):
                payload = result.payload
                score = getattr(
                    result,
                    "score",
                    None
                )
            else:
                payload = result
                score = None

            print(
                "\n" +
                "=" * 80
            )

            print(
                f"Rank: {idx}"
            )

            if score is not None:

                print(
                    f"Score: "
                    f"{score:.4f}"
                )

            print(
                f"Chunk ID: "
                f"{payload.get('chunk_id')}"
            )

            print(
                f"Type: "
                f"{payload.get('chunk_type')}"
            )

            print(
                f"Article: "
                f"{payload.get('article_no')}"
            )

            print(
                f"Title: "
                f"{payload.get('article_title')}"
            )

            print("\nTEXT:\n")

            print(
                payload.get(
                    "text",
                    ""
                )[:2000]
            )

    # =====================================================
    # CONTEXT BUILDER
    # =====================================================

    def retrieve_context(
        self,
        query: str,
        top_k: int = 5
    ):

        results = self.search(
            query,
            top_k
        )

        context = []

        for result in results:

            payload = result.payload

            context.append(
                payload.get(
                    "text",
                    ""
                )
            )

        return "\n\n".join(
            context
        )


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    search_engine = ConstitutionSearch(
        collection_name=
            "constitution",

        qdrant_url=
            "http://localhost:6333"
    )

    query = (
        "What is the right to equality?"
    )

    results = search_engine.search(
        query,
        top_k=5
    )

    search_engine.print_results(
        results
    )