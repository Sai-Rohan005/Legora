from neo4j import GraphDatabase


class LegalGraphDB:

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # --------------------------------------------------
    # INSERT CHUNKS
    # --------------------------------------------------

    def insert_chunks(self, chunks):

        with self.driver.session() as session:

            for chunk in chunks:

                chunk_type = chunk["type"]
                text = chunk["text"]

                meta = chunk.get("meta", {}) or {}

                document = meta.get("document")

                embedding = chunk.get("embedding")
                if hasattr(embedding, "tolist"):
                    embedding = embedding.tolist()

                # ==================================================
                # DIVISION
                # ==================================================

                if chunk_type == "division":

                    props = {
                        "document": document,
                        "chunk_type": "division",
                        "division_no": meta["division_no"],
                        "text": text,
                    }

                    if embedding is not None:
                        props["embedding"] = embedding

                    session.run(
                        """
                        MERGE (d:LegalChunk:Division {
                            document:$document,
                            division_no:$division_no
                        })

                        SET d += $props
                        """,
                        document=document,
                        division_no=meta["division_no"],
                        props=props
                    )

                # ==================================================
                # PROVISION
                # ==================================================

                elif chunk_type == "provision":

                    props = {
                        "document": document,
                        "chunk_type": "provision",
                        "division_no": meta.get("division_no"),
                        "provision_no": meta["provision_no"],
                        "title": meta.get("title"),
                        "text": text,
                    }

                    if embedding is not None:
                        props["embedding"] = embedding

                    session.run(
                        """
                        MERGE (p:LegalChunk:Provision {
                            document:$document,
                            provision_no:$provision_no
                        })

                        SET p += $props

                        WITH p

                        OPTIONAL MATCH (d:Division {
                            document:$document,
                            division_no:$division_no
                        })

                        FOREACH (_ IN CASE WHEN d IS NULL THEN [] ELSE [1] END |
                            MERGE (d)-[:HAS_PROVISION]->(p)
                        )
                        """,
                        document=document,
                        provision_no=meta["provision_no"],
                        division_no=meta.get("division_no"),
                        props=props
                    )

                # ==================================================
                # CLAUSE
                # ==================================================

                elif chunk_type == "clause":

                    props = {
                        "document": document,
                        "chunk_type": "clause",
                        "provision_no": meta["provision_no"],
                        "clause_no": meta["clause_no"],
                        "text": text,
                    }

                    if embedding is not None:
                        props["embedding"] = embedding

                    session.run(
                        """
                        MERGE (c:LegalChunk:Clause {
                            document:$document,
                            provision_no:$provision_no,
                            clause_no:$clause_no
                        })

                        SET c += $props

                        WITH c

                        MATCH (p:Provision {
                            document:$document,
                            provision_no:$provision_no
                        })

                        MERGE (p)-[:HAS_CLAUSE]->(c)
                        """,
                        document=document,
                        provision_no=meta["provision_no"],
                        clause_no=meta["clause_no"],
                        props=props
                    )

                # ==================================================
                # SUBCLAUSE
                # ==================================================

                elif chunk_type == "subclause":

                    props = {
                        "document": document,
                        "chunk_type": "subclause",
                        "provision_no": meta["provision_no"],
                        "clause_no": meta["clause_no"],
                        "subclause_no": meta["sub_clause_no"],
                        "text": text,
                    }

                    if embedding is not None:
                        props["embedding"] = embedding

                    session.run(
                        """
                        MERGE (s:LegalChunk:Subclause {
                            document:$document,
                            provision_no:$provision_no,
                            clause_no:$clause_no,
                            subclause_no:$subclause_no
                        })

                        SET s += $props

                        WITH s

                        MATCH (c:Clause {
                            document:$document,
                            provision_no:$provision_no,
                            clause_no:$clause_no
                        })

                        MERGE (c)-[:HAS_SUBCLAUSE]->(s)
                        """,
                        document=document,
                        provision_no=meta["provision_no"],
                        clause_no=meta["clause_no"],
                        subclause_no=meta["sub_clause_no"],
                        props=props
                    )

                # ==================================================
                # ROMAN
                # ==================================================

                elif chunk_type == "roman":

                    props = {
                        "document": document,
                        "chunk_type": "roman",
                        "provision_no": meta["provision_no"],
                        "clause_no": meta["clause_no"],
                        "subclause_no": meta["sub_clause_no"],
                        "roman_no": meta["roman_no"],
                        "text": text,
                    }

                    if embedding is not None:
                        props["embedding"] = embedding

                    session.run(
                        """
                        MERGE (r:LegalChunk:Roman {
                            document:$document,
                            provision_no:$provision_no,
                            clause_no:$clause_no,
                            subclause_no:$subclause_no,
                            roman_no:$roman_no
                        })

                        SET r += $props

                        WITH r

                        MATCH (s:Subclause {
                            document:$document,
                            provision_no:$provision_no,
                            clause_no:$clause_no,
                            subclause_no:$subclause_no
                        })

                        MERGE (s)-[:HAS_ROMAN]->(r)
                        """,
                        document=document,
                        provision_no=meta["provision_no"],
                        clause_no=meta["clause_no"],
                        subclause_no=meta["sub_clause_no"],
                        roman_no=meta["roman_no"],
                        props=props
                    )

                else:
                    raise ValueError(
                        f"Unsupported chunk type: {chunk_type}"
                    )