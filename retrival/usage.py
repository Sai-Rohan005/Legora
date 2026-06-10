from retrival.cross_encoder import LegalReranker
from retrival.singleton_loader import AppContext


def retrieve_similar_cases(query, top_k=5):

    # -------------------------
    # SINGLETONS (NO RELOAD)
    # -------------------------
    embedder = AppContext.get_embedder()
    qdrant = AppContext.get_qdrant()
    graph = AppContext.get_graph()

    # -------------------------
    # EMBEDDING
    # -------------------------
    query_embedding = embedder.encode([query])[0]

    # -------------------------
    # VECTOR SEARCH (QDRANT)
    # -------------------------
    results = qdrant.search(
        query_vector=query_embedding.tolist(),
        limit=top_k
    )
    # print("qdrant results:", results)
    # -------------------------
    # GRAPH ENRICHMENT (FIXED)
    # -------------------------
    ids = [r.id for r in results]

    with graph.driver.session() as session:
        cypher = """
        MATCH (n:LegalChunk)
        WHERE n.id IN $ids
        RETURN n.embedding_text AS text, n.metadata AS metadata
        """

        graph_result = session.run(cypher, ids=ids)

        graph_docs = [
            {
                "text": r["text"],
                "metadata": r["metadata"]
            }
            for r in graph_result
        ]

    # -------------------------
    # RERANKING (CROSS ENCODER)
    # -------------------------
    reranker = LegalReranker()

    combined_results = [
        {
            "text": r.payload.get("embedding_text"),
            "metadata": r.payload,
            "score": r.score
        }
        for r in results
    ]

    reranked_results = reranker.rerank(
        query=query,
        results=combined_results,
        top_k=top_k
    )

    return reranked_results

print(retrieve_similar_cases("What does Article 14 of the Indian Constitution say?", top_k=5))