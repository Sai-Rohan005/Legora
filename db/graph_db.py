from neo4j import GraphDatabase


class LegalGraphDB:

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # --------------------------------------------------
    # INSERT CHUNKS (CLEAN + SAFE)
    # --------------------------------------------------

    def insert_chunks(self, records):

        with self.driver.session() as session:

            for record in records:

                metadata = record.get("metadata", {}) or {}

                embedding = record.get("embedding")

                if hasattr(embedding, "tolist"):
                    embedding = embedding.tolist()

                # -----------------------------
                # CORE NODE PROPERTIES
                # -----------------------------
                props = {
                    "id": record["id"],
                    "document_type": record["document_type"],
                    "chunk_type": record["chunk_type"],
                    "text": record["embedding_text"],
                }

                # -----------------------------
                # ADD METADATA (FLAT ONLY)
                # -----------------------------
                props.update(metadata)

                # -----------------------------
                # ADD EMBEDDING (OPTIONAL)
                # -----------------------------
                if embedding is not None:
                    props["embedding"] = embedding

                # -----------------------------
                # CREATE NODE
                # -----------------------------
                session.run(
                    """
                    MERGE (n:LegalChunk {id: $id})
                    SET n += $props
                    """,
                    id=record["id"],
                    props=props
                )

    # --------------------------------------------------
    # VECTOR INDEX
    # --------------------------------------------------

    def create_vector_index(
        self,
        dimensions: int = 1024,
        index_name: str = "legal_embeddings"
    ):

        with self.driver.session() as session:

            session.run(f"""
                CREATE VECTOR INDEX {index_name} IF NOT EXISTS
                FOR (n:LegalChunk)
                ON (n.embedding)
                OPTIONS {{
                    indexConfig: {{
                        `vector.dimensions`: {dimensions},
                        `vector.similarity_function`: 'cosine'
                    }}
                }}
            """)

    # --------------------------------------------------
    # VECTOR SEARCH
    # --------------------------------------------------

    def vector_search(self, embedding, top_k: int = 10, index_name="legal_embeddings"):

        if hasattr(embedding, "tolist"):
            embedding = embedding.tolist()

        with self.driver.session() as session:

            result = session.run(
                """
                CALL db.index.vector.queryNodes(
                    $index_name,
                    $top_k,
                    $embedding
                )
                YIELD node, score

                RETURN
                    node.id AS id,
                    node.chunk_type AS chunk_type,
                    node.document_type AS document_type,
                    node.text AS text,
                    score
                ORDER BY score DESC
                """,
                index_name=index_name,
                top_k=top_k,
                embedding=embedding
            )

            return [dict(r) for r in result]

    # --------------------------------------------------
    # UTILITIES
    # --------------------------------------------------

    def count_chunks(self):
        with self.driver.session() as session:
            return session.run(
                "MATCH (n:LegalChunk) RETURN count(n) AS total"
            ).single()["total"]

    def clear(self):
        with self.driver.session() as session:
            session.run("MATCH (n:LegalChunk) DETACH DELETE n")