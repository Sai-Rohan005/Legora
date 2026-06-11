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

    print("🔍 Qdrant results:", len(results))

    # ---------------------------------
    # EXTRACT PROVISIONS (from vector hits)
    # ---------------------------------
    provision_nos = list({
        r.payload.get("provision_no")
        for r in results
        if r.payload and r.payload.get("provision_no")
    })

    graph_docs = []

    # ---------------------------------
    # GRAPH ENRICHMENT (WITH IDS)
    # ---------------------------------
    if provision_nos:

        with graph.driver.session() as session:

            cypher = """
            MATCH (p:LegalChunk:Provision)
            WHERE p.provision_no IN $provision_nos

            OPTIONAL MATCH (p)-[:HAS_CLAUSE]->(c:LegalChunk:Clause)
            OPTIONAL MATCH (c)-[:HAS_SUBCLAUSE]->(s:LegalChunk:Subclause)
            OPTIONAL MATCH (s)-[:HAS_ROMAN]->(r:LegalChunk:Roman)

            RETURN
                p.provision_no AS provision_no,
                p.title AS title,
                p.text AS provision_text,
                collect(DISTINCT c.text) AS clauses,
                collect(DISTINCT s.text) AS subclauses,
                collect(DISTINCT r.text) AS romans
            """

            records = session.run(cypher, provision_nos=provision_nos)

            for rec in records:

                text_parts = []

                if rec["provision_text"]:
                    text_parts.append(rec["provision_text"])

                text_parts += [c for c in rec["clauses"] if c]
                text_parts += [s for s in rec["subclauses"] if s]
                text_parts += [r for r in rec["romans"] if r]

                graph_docs.append({
                    # IMPORTANT: graph-context ID (deterministic fallback)
                    "id": f"graph:{rec['provision_no']}",

                    "text": "\n\n".join(text_parts),

                    "metadata": {
                        "chunk_type": "graph_context",
                        "provision_no": rec["provision_no"],
                        "title": rec["title"]
                    },

                    "score": 0.90
                })

    print("🔍 Graph enrichment results:", len(graph_docs))

    # ---------------------------------
    # MERGE VECTOR + GRAPH RESULTS
    # ---------------------------------
    combined_results = []

    for r in results:

        payload = r.payload or {}

        text = (
            payload.get("text")
            or payload.get("content")
            or payload.get("embedding_text")
        )

        if not text:
            continue

        combined_results.append({
            # CRITICAL: Qdrant ID preserved
            "id": payload.get("id"),

            "text": text,
            "metadata": payload,
            "score": r.score
        })

    combined_results.extend(graph_docs)

    # ---------------------------------
    # DEDUP (NOW ID-BASED, NOT TEXT-BASED)
    # ---------------------------------
    cleaned_results = []
    seen = set()

    for r in combined_results:

        rid = r.get("id")

        # fallback safety if id missing
        if not rid:
            rid = r["text"].strip()

        if rid in seen:
            continue

        seen.add(rid)
        cleaned_results.append(r)

    # ---------------------------------
    # RERANK
    # ---------------------------------
    reranker = LegalReranker()

    reranked = reranker.rerank(
        query=query,
        results=cleaned_results,
        top_k=top_k
    )

    # ---------------------------------
    # ENSURE IDs SURVIVE FINAL OUTPUT
    # ---------------------------------
    return [
        {
            "id": r.get("id"),
            "text": r["text"],
            "metadata": r.get("metadata", {}),
            "score": r.get("score"),
            "rerank_score": r.get("rerank_score")
        }
        for r in reranked
    ]


# ---------------------------------
# TEST
# ---------------------------------
print(
    retrieve_similar_cases(
        "What does Article 14 of the Indian Constitution say?",
        top_k=5
    )
)