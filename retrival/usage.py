from retrival.cross_encoder import LegalReranker
from retrival.singleton_loader import AppContext


def retrieve_similar_cases(query, top_k=5):

    embedder = AppContext.get_embedder()
    qdrant = AppContext.get_qdrant()
    graph = AppContext.get_graph()

    # ---------------------------------
    # EMBEDDING
    # ---------------------------------

    query_embedding = embedder.encode([query])[0]

    # ---------------------------------
    # QDRANT SEARCH
    # ---------------------------------

    results = qdrant.search(
        query_vector=query_embedding.tolist(),
        limit=top_k
    )

    print("🔍 Qdrant results", results)

    # ---------------------------------
    # EXTRACT PROVISIONS FOR GRAPH LOOKUP
    # ---------------------------------

    provision_nos = list({
        r.payload.get("provision_no")
        for r in results
        if r.payload and r.payload.get("provision_no")
    })

    # ---------------------------------
    # GRAPH ENRICHMENT
    # ---------------------------------

    graph_docs = []

    if provision_nos:

        with graph.driver.session() as session:

            cypher = """
            MATCH (p:Provision)
            WHERE p.provision_no IN $provision_nos

            OPTIONAL MATCH (p)-[:HAS_CLAUSE]->(c:Clause)
            OPTIONAL MATCH (c)-[:HAS_SUBCLAUSE]->(s:Subclause)
            OPTIONAL MATCH (s)-[:HAS_ROMAN]->(r:Roman)

            RETURN
                p.provision_no AS provision_no,
                p.title AS title,
                p.text AS provision_text,
                collect(DISTINCT c.text) AS clauses,
                collect(DISTINCT s.text) AS subclauses,
                collect(DISTINCT r.text) AS romans
            """

            records = session.run(
                cypher,
                provision_nos=provision_nos
            )

            for rec in records:

                text_parts = []

                if rec["provision_text"]:
                    text_parts.append(rec["provision_text"])

                for clause in rec["clauses"]:
                    if clause:
                        text_parts.append(clause)

                for subclause in rec["subclauses"]:
                    if subclause:
                        text_parts.append(subclause)

                for roman in rec["romans"]:
                    if roman:
                        text_parts.append(roman)

                graph_docs.append(
                    {
                        "text": "\n\n".join(text_parts),
                        "metadata": {
                            "chunk_type": "graph_context",
                            "provision_no": rec["provision_no"],
                            "title": rec["title"]
                        }
                    }
                )

    print("🔍 Graph enrichment results", graph_docs)

    # ---------------------------------
    # MERGE RESULTS
    # ---------------------------------

    combined_results = []

    # Original Qdrant hits

    for r in results:

        payload = r.payload or {}

        text = (
            payload.get("text")
            or payload.get("content")
            or payload.get("embedding_text")
        )

        combined_results.append(
            {
                "text": text,
                "metadata": payload,
                "score": r.score
            }
        )

    # Graph enriched context

    for doc in graph_docs:

        combined_results.append(
            {
                "text": doc["text"],
                "metadata": doc["metadata"],
                "score": 0.95
            }
        )

    # ---------------------------------
    # CLEAN
    # ---------------------------------

    cleaned_results = []

    seen = set()

    for r in combined_results:

        text = r.get("text")

        if not text:
            continue

        if text in seen:
            continue

        seen.add(text)

        cleaned_results.append(r)

    # ---------------------------------
    # RERANK
    # ---------------------------------

    reranker = LegalReranker()

    reranked_results = reranker.rerank(
        query=query,
        results=cleaned_results,
        top_k=top_k
    )

    return reranked_results

print(
    retrieve_similar_cases(
        "What does Article 14 of the Indian Constitution say?",
        top_k=5
    )
)