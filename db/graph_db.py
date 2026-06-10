from neo4j import GraphDatabase


class LegalGraphDB:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # -----------------------------
    # INSERT STRUCTURE (IDEMPOTENT)
    # -----------------------------

    def insert_structure(self, parts):

        with self.driver.session() as session:

            for part in parts:

                part_id = f"PART-{part.part_no}"

                session.run("""
                    MERGE (p:Part {id:$id})
                    SET p.number=$number,
                        p.title=$title
                """,
                id=part_id,
                number=part.part_no,
                title=part.part_title)

                for article in part.articles:

                    article_id = (
                        f"{part_id}-ARTICLE-{article.article_no}"
                    )

                    session.run("""
                        MERGE (a:Article {id:$id})
                        SET a.number=$number,
                            a.title=$title,
                            a.text=$text

                        WITH a

                        MATCH (p:Part {id:$part_id})

                        MERGE (p)-[:HAS_ARTICLE]->(a)
                    """,
                    id=article_id,
                    number=article.article_no,
                    title=article.article_title,
                    text=article.text,
                    part_id=part_id)

                    # ----------------------------------
                    # REFERENCES
                    # ----------------------------------

                    for ref in article.references:

                        ref_id = f"ARTICLE-{ref.article_no}"

                        session.run("""
                            MERGE (r:ArticleRef {id:$id})

                            SET r.number=$number

                            WITH r

                            MATCH (a:Article {id:$article_id})

                            MERGE (a)-[:REFERENCES]->(r)
                        """,
                        id=ref_id,
                        number=ref.article_no,
                        article_id=article_id)

                    # ----------------------------------
                    # PROVISOS
                    # ----------------------------------

                    for idx, proviso in enumerate(
                        article.provisos
                    ):

                        proviso_id = (
                            f"{article_id}-PROVISO-{idx}"
                        )

                        session.run("""
                            MERGE (p:Proviso {id:$id})

                            SET p.text=$text

                            WITH p

                            MATCH (a:Article {id:$article_id})

                            MERGE (a)-[:HAS_PROVISO]->(p)
                        """,
                        id=proviso_id,
                        text=proviso.text,
                        article_id=article_id)

                    # ----------------------------------
                    # EXPLANATIONS
                    # ----------------------------------

                    for idx, explanation in enumerate(
                        article.explanations
                    ):

                        explanation_id = (
                            f"{article_id}-EXPLANATION-{idx}"
                        )

                        session.run("""
                            MERGE (e:Explanation {id:$id})

                            SET e.text=$text

                            WITH e

                            MATCH (a:Article {id:$article_id})

                            MERGE (a)-[:HAS_EXPLANATION]->(e)
                        """,
                        id=explanation_id,
                        text=explanation.text,
                        article_id=article_id)

                    # ----------------------------------
                    # CLAUSES
                    # ----------------------------------

                    for clause in article.clauses:

                        clause_id = (
                            f"{article_id}-CLAUSE-{clause.clause_no}"
                        )

                        session.run("""
                            MERGE (c:Clause {id:$id})

                            SET c.number=$number,
                                c.text=$text

                            WITH c

                            MATCH (a:Article {id:$article_id})

                            MERGE (a)-[:HAS_CLAUSE]->(c)
                        """,
                        id=clause_id,
                        number=clause.clause_no,
                        text=clause.text,
                        article_id=article_id)

                        # ------------------------------
                        # SUBCLAUSES
                        # ------------------------------

                        for sub in clause.sub_clauses:

                            sub_id = (
                                f"{clause_id}-SUB-{sub.sub_clause_no}"
                            )

                            session.run("""
                                MERGE (s:SubClause {id:$id})

                                SET s.number=$number,
                                    s.text=$text

                                WITH s

                                MATCH (c:Clause {id:$clause_id})

                                MERGE (c)-[:HAS_SUBCLAUSE]->(s)
                            """,
                            id=sub_id,
                            number=sub.sub_clause_no,
                            text=sub.text,
                            clause_id=clause_id)

                            # --------------------------
                            # ROMAN CLAUSES
                            # --------------------------

                            for roman in sub.roman_clauses:

                                roman_id = (
                                    f"{sub_id}-ROMAN-{roman.roman_no}"
                                )

                                session.run("""
                                    MERGE (r:RomanClause {id:$id})

                                    SET r.number=$number,
                                        r.text=$text

                                    WITH r

                                    MATCH (s:SubClause {
                                        id:$sub_id
                                    })

                                    MERGE (s)-[:HAS_ROMAN]->(r)
                                """,
                                id=roman_id,
                                number=roman.roman_no,
                                text=roman.text,
                                sub_id=sub_id)