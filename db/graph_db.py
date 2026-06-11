from neo4j import GraphDatabase


class LegalGraphDB:

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clean(self, d):
        return {k: v for k, v in d.items() if v is not None}

    def insert_chunks(self, chunks):

        with self.driver.session() as session:

            for chunk in chunks:

                chunk_type = chunk.get("type")
                text = chunk.get("text", "")
                meta = chunk.get("meta", {}) or {}

                embedding = chunk.get("embedding")
                if hasattr(embedding, "tolist"):
                    embedding = embedding.tolist()

                document = meta.get("document")
                if not document:
                    print(f"Skipping chunk (missing document): {text[:40]}")
                    continue

                # ==================================================
                # DIVISION
                # ==================================================
                if chunk_type == "division":

                    division_no = meta.get("division_no")
                    if not division_no:
                        continue

                    props = self.clean({
                        "document": document,
                        "chunk_type": "division",
                        "division_no": division_no,
                        "text": text,
                        "embedding": embedding
                    })

                    session.run(
                        """
                        MERGE (d:LegalChunk:Division {
                            document: $document,
                            division_no: $division_no
                        })
                        SET d += $props
                        """,
                        document=document,
                        division_no=division_no,
                        props=props
                    )

                # ==================================================
                # PROVISION
                # ==================================================
                elif chunk_type == "provision":

                    provision_no = meta.get("provision_no")
                    division_no = meta.get("division_no")

                    if not provision_no:
                        continue

                    props = self.clean({
                        "document": document,
                        "chunk_type": "provision",
                        "division_no": division_no,
                        "provision_no": provision_no,
                        "title": meta.get("title"),
                        "text": text,
                        "embedding": embedding
                    })

                    session.run(
                        """
                        MERGE (p:LegalChunk:Provision {
                            document: $document,
                            provision_no: $provision_no
                        })
                        SET p += $props

                        WITH p
                        OPTIONAL MATCH (d:LegalChunk:Division {
                            document: $document,
                            division_no: $division_no
                        })
                        FOREACH (_ IN CASE WHEN d IS NULL THEN [] ELSE [1] END |
                            MERGE (d)-[:HAS_PROVISION]->(p)
                        )
                        """,
                        document=document,
                        provision_no=provision_no,
                        division_no=division_no,
                        props=props
                    )

                # ==================================================
                # CLAUSE
                # ==================================================
                elif chunk_type == "clause":

                    provision_no = meta.get("provision_no")
                    clause_no = meta.get("clause_no")

                    if not (provision_no and clause_no):
                        continue

                    props = self.clean({
                        "document": document,
                        "chunk_type": "clause",
                        "provision_no": provision_no,
                        "clause_no": clause_no,
                        "text": text,
                        "embedding": embedding
                    })

                    session.run(
                        """
                        MERGE (c:LegalChunk:Clause {
                            document: $document,
                            provision_no: $provision_no,
                            clause_no: $clause_no
                        })
                        SET c += $props

                        WITH c
                        OPTIONAL MATCH (p:LegalChunk:Provision {
                            document: $document,
                            provision_no: $provision_no
                        })
                        FOREACH (_ IN CASE WHEN p IS NULL THEN [] ELSE [1] END |
                            MERGE (p)-[:HAS_CLAUSE]->(c)
                        )
                        """,
                        document=document,
                        provision_no=provision_no,
                        clause_no=clause_no,
                        props=props
                    )

                # ==================================================
                # SUBCLAUSE (FIXED)
                # ==================================================
                elif chunk_type == "subclause":

                    provision_no = meta.get("provision_no")
                    clause_no = meta.get("clause_no")
                    sub_clause_no = meta.get("sub_clause_no")

                    if not (provision_no and clause_no and sub_clause_no):
                        continue

                    props = self.clean({
                        "document": document,
                        "chunk_type": "subclause",
                        "provision_no": provision_no,
                        "clause_no": clause_no,
                        "sub_clause_no": sub_clause_no,
                        "text": text,
                        "embedding": embedding
                    })

                    session.run(
                        """
                        MERGE (s:LegalChunk:Subclause {
                            document: $document,
                            provision_no: $provision_no,
                            clause_no: $clause_no,
                            sub_clause_no: $sub_clause_no
                        })
                        SET s += $props

                        WITH s
                        OPTIONAL MATCH (c:LegalChunk:Clause {
                            document: $document,
                            provision_no: $provision_no,
                            clause_no: $clause_no
                        })
                        FOREACH (_ IN CASE WHEN c IS NULL THEN [] ELSE [1] END |
                            MERGE (c)-[:HAS_SUBCLAUSE]->(s)
                        )
                        """,
                        document=document,
                        provision_no=provision_no,
                        clause_no=clause_no,
                        sub_clause_no=sub_clause_no,
                        props=props
                    )

                # ==================================================
                # ROMAN (FIXED)
                # ==================================================
                elif chunk_type == "roman":

                    provision_no = meta.get("provision_no")
                    clause_no = meta.get("clause_no")
                    sub_clause_no = meta.get("sub_clause_no")
                    roman_no = meta.get("roman_no")

                    if not (provision_no and clause_no and sub_clause_no and roman_no):
                        continue

                    props = self.clean({
                        "document": document,
                        "chunk_type": "roman",
                        "provision_no": provision_no,
                        "clause_no": clause_no,
                        "sub_clause_no": sub_clause_no,
                        "roman_no": roman_no,
                        "text": text,
                        "embedding": embedding
                    })

                    session.run(
                        """
                        MERGE (r:LegalChunk:Roman {
                            document: $document,
                            provision_no: $provision_no,
                            clause_no: $clause_no,
                            sub_clause_no: $sub_clause_no,
                            roman_no: $roman_no
                        })
                        SET r += $props

                        WITH r
                        OPTIONAL MATCH (s:LegalChunk:Subclause {
                            document: $document,
                            provision_no: $provision_no,
                            clause_no: $clause_no,
                            sub_clause_no: $sub_clause_no
                        })
                        FOREACH (_ IN CASE WHEN s IS NULL THEN [] ELSE [1] END |
                            MERGE (s)-[:HAS_ROMAN]->(r)
                        )
                        """,
                        document=document,
                        provision_no=provision_no,
                        clause_no=clause_no,
                        sub_clause_no=sub_clause_no,
                        roman_no=roman_no,
                        props=props
                    )

                else:
                    print(f"Unknown chunk type: {chunk_type}")