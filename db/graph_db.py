from neo4j import GraphDatabase


class LegalGraphDB:

    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    # -----------------------------
    # INSERT STRUCTURE (IDEMPOTENT)
    # -----------------------------

    def insert_structure(self, parsed_data):

        with self.driver.session() as session:

            for part in parsed_data["parts"]:

                part_id = f"PART-{part['part_no']}"

                # -----------------
                # PART (UNIQUE)
                # -----------------
                session.run("""
                    MERGE (p:Part {id: $id})
                    SET p.number = $number,
                        p.title = $title
                """,
                id=part_id,
                number=part["part_no"],
                title=part["part_title"])

                for article in part["articles"]:

                    article_id = f"{part_id}-{article['article_no']}"

                    # -----------------
                    # ARTICLE (UNIQUE)
                    # -----------------
                    session.run("""
                        MERGE (a:Article {id: $id})
                        SET a.number = $number,
                            a.text = $text
                        WITH a
                        MATCH (p:Part {id: $part_id})
                        MERGE (p)-[:HAS_ARTICLE]->(a)
                    """,
                    id=article_id,
                    number=article["article_no"],
                    text=article["text"],
                    part_id=part_id)

                    for clause in article.get("clauses", []):

                        clause_id = f"{article_id}-{clause['clause_no']}"

                        # -----------------
                        # CLAUSE (UNIQUE)
                        # -----------------
                        session.run("""
                            MERGE (c:Clause {id: $id})
                            SET c.number = $number,
                                c.text = $text
                            WITH c
                            MATCH (a:Article {id: $article_id})
                            MERGE (a)-[:HAS_CLAUSE]->(c)
                        """,
                        id=clause_id,
                        number=clause["clause_no"],
                        text=clause["text"],
                        article_id=article_id)