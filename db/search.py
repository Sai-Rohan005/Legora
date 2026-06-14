from __future__ import annotations

from db.embedder import (
    LegalEmbedder
)

from db.vector_store import (
    QdrantStore
)
from db.neo4j_store import Neo4jStore

from symspellpy import SymSpell, Verbosity

sym_spell = SymSpell(
    max_dictionary_edit_distance=2,
    prefix_length=7
)

sym_spell.load_dictionary(
    "frequency_dictionary_en_82_765.txt",
    term_index=0,
    count_index=1
)


def spell_correct(text: str) -> str:

    suggestions = sym_spell.lookup_compound(
        text,
        max_edit_distance=2
    )

    if suggestions:
        return suggestions[0].term

    return text





class LegalRetriever:

    def __init__(
        self,
        collection_name: str = "legal_rag"
    ):

        self.embedder = (
            LegalEmbedder()
        )

        self.qdrant = (
            QdrantStore(
                collection_name=
                    collection_name
            )
        )

        self.graph = (
            Neo4jStore(
                uri="bolt://localhost:7687",
                username="neo4j",
                password="password"
            )
        )

    # =====================================================
    # VECTOR SEARCH
    # =====================================================

    def vector_search(
        self,
        query: str,
        limit: int = 10
    ):

        query_vector = (
            self.embedder
            .embed_query(
                query
            )
        )

        results = (
            self.qdrant.search(
                query_vector,
                limit
            )
        )

        return results.points

    # =====================================================
    # NODE EXTRACTION
    # =====================================================

    def extract_nodes(
        self,
        points
    ):

        nodes = []

        seen = set()

        for point in points:

            payload = point.payload

            node_id = payload.get(
                "node_id"
            )

            node_type = payload.get(
                "node_type"
            )

            if not node_id:
                continue

            if node_id in seen:
                continue

            seen.add(
                node_id
            )

            nodes.append(
                {
                    "node_id":
                        node_id,

                    "node_type":
                        node_type,

                    "document":
                        payload.get(
                            "document"
                        )
                }
            )

        return nodes

    # =====================================================
    # SECTION EXPANSION
    # =====================================================

    def expand_section(
        self,
        node_id: str
    ):

        query = """
        MATCH (s:Section {id:$id})

        OPTIONAL MATCH (s)-[:HAS_CLAUSE]->(c)

        OPTIONAL MATCH (s)-[:HAS_EXPLANATION]->(e)

        OPTIONAL MATCH (s)-[:HAS_ILLUSTRATION]->(i)

        OPTIONAL MATCH (s)-[:REFERENCES]->(r)

        RETURN
            s,
            collect(distinct c) as clauses,
            collect(distinct e) as explanations,
            collect(distinct i) as illustrations,
            collect(distinct r) as references
        """

        return (
            self.graph.run_query(
                query,
                {
                    "id": node_id
                }
            )
        )

    # =====================================================
    # ARTICLE EXPANSION
    # =====================================================

    def expand_article(
        self,
        node_id: str
    ):

        query = """
        MATCH (a:Article {id:$id})

        OPTIONAL MATCH (a)-[:HAS_CLAUSE]->(c)

        OPTIONAL MATCH (a)-[:HAS_PROVISO]->(p)

        OPTIONAL MATCH (a)-[:HAS_EXPLANATION]->(e)

        OPTIONAL MATCH (a)-[:REFERENCES]->(r)

        RETURN
            a,
            collect(distinct c) as clauses,
            collect(distinct p) as provisos,
            collect(distinct e) as explanations,
            collect(distinct r) as references
        """

        return (
            self.graph.run_query(
                query,
                {
                    "id": node_id
                }
            )
        )

    # =====================================================
    # CLAUSE EXPANSION
    # =====================================================

    def expand_clause(
        self,
        node_id: str
    ):

        query = """
        MATCH (c:Clause {id:$id})

        OPTIONAL MATCH (c)-[:HAS_SUBCLAUSE]->(s)

        RETURN
            c,
            collect(distinct s) as subclauses
        """

        return (
            self.graph.run_query(
                query,
                {
                    "id": node_id
                }
            )
        )

    # =====================================================
    # GENERIC EXPANSION
    # =====================================================

    def expand_node(
        self,
        node
    ):

        node_type = (
            node["node_type"]
        )

        node_id = (
            node["node_id"]
        )

        if node_type == "Section":

            return self.expand_section(
                node_id
            )

        if node_type == "Article":

            return self.expand_article(
                node_id
            )

        if node_type == "Clause":

            return self.expand_clause(
                node_id
            )

        return []

    # =====================================================
    # HYBRID RETRIEVAL
    # =====================================================

    def retrieve(
        self,
        query: str,
        vector_k: int = 10
    ):

        vector_points = (
            self.vector_search(
                query,
                vector_k
            )
        )

        nodes = (
            self.extract_nodes(
                vector_points
            )
        )

        graph_context = []

        for node in nodes:

            graph_context.extend(
                self.expand_node(
                    node
                )
            )

        return {
            "query":
                query,

            "vector_results":
                vector_points,

            "expanded_nodes":
                nodes,

            "graph_context":
                graph_context
        }
# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    searcher = (
        LegalRetriever(
            collection_name=
                "legal_rag"
        )
    )
    hard_queries = [
    "attemptive mudder",
        "can police arrest me without magistrate permission",
        "facts accepted by court without proof",
        "government cannot take away my freedom without following law",
        "computer records admissible in court",
        "person killed while protecting property from robbery",
        "proof responsibility of accused",
        "maximum time police can keep arrested person before court",
        "freedom of speech restrictions",
        "when witness statement can be used after witness dies",
        "person dies after making statement explaining cause of death"
    ]
    expert_queries = [
        "attemptive mudder",
        "judical notice",
        "burdan of proof",
        "wife can testify against husband in criminal case",
        "secondary evidence of lost document",
        "statement made before death about cause of death",
        "when police officer can arrest without warrant",
        "person resisting lawful apprehension",
        "right of private defence causing death",
        "electronic record certificate requirements",
        "facts court must presume unless disproved",
        "who has burden of proving exception in criminal case",
        "anticipatory bail before arrest",
        "public document versus private document",
        "admission made by agent binding principal",
        "constitutional remedy against state action",
        "freedom of speech reasonable restrictions",
        "offence committed outside india by indian citizen",
        "confession made to police officer admissibility",
        "expert opinion relevance in court"
    ]



    output_file = "retrieval_results.txt"

    with open(output_file, "w", encoding="utf-8") as f:

        for query in hard_queries:
            query = spell_correct(query)

            if not query:
                continue

            results = searcher.search(
                query=query,
                limit=10
            )

            f.write("=" * 100 + "\n")
            f.write(f"QUERY: {query}\n")
            f.write("=" * 100 + "\n\n")

            for rank, result in enumerate(results, start=1):
                f.write(f"Rank {rank}\n")
                f.write(str(result))
                f.write("\n\n")

    print(f"Results saved to {output_file}")





    # for query in hard_queries:

    #     if not query:

    #         continue

    #     if query.lower() in {
    #         "exit",
    #         "quit"
    #     }:
    #         break

    #     results = (
    #         searcher.search(
    #             query=query,
    #             limit=10
    #         )
    #     )

    #     searcher.print_results(
    #         results
    #     )