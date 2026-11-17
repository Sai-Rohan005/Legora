from __future__ import annotations

import logging
from builtins import str

from neo4j import GraphDatabase, Query
from legora.config import EvaluationSettings, Settings, get_settings
from legora.performance import call_external

logger = logging.getLogger(__name__)
class Neo4jStore:

    def __init__(self, settings: Settings | EvaluationSettings | None = None) -> None:
        """Create a driver from required NEO4J_* environment variables."""
        config = settings or get_settings()
        missing = [name for name, value in (
            ("NEO4J_URI", config.neo4j_uri), ("NEO4J_USERNAME", config.neo4j_username),
            ("NEO4J_PASSWORD", config.neo4j_password.get_secret_value() if config.neo4j_password else None),
        ) if not value or not value.strip()]
        if missing:
            raise ValueError("Missing required Neo4j environment variables: " + ", ".join(missing))
        self.timeout = config.external_timeout_seconds
        self.driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_username, config.neo4j_password.get_secret_value()),
            connection_timeout=self.timeout,
            connection_acquisition_timeout=self.timeout,
            connection_write_timeout=self.timeout,
            max_transaction_retry_time=0
        )

    # =====================================================
    # CLOSE
    # =====================================================

    def close(self):

        self.driver.close()

    # =====================================================
    # EXECUTE
    # =====================================================

    def execute(
        self,
        query: str,
        parameters: dict | None = None
    ):

        with self.driver.session() as session:

            result= session.run(
                Query(query, timeout=self.timeout),
                parameters or {}
            )
            return list(result)

    # =====================================================
    # RUN QUERY
    # =====================================================

    def run_query(
        self,
        query: str,
        parameters: dict | None = None
    ):

        result = call_external(self.execute,
            query,
            parameters
        )

        return [
            record.data()
            for record in result
        ]

    # =====================================================
    # CLEAR GRAPH
    # =====================================================

    def clear_graph(self):

        self.execute(
            """
            MATCH (n)
            DETACH DELETE n
            """
        )

    # =====================================================
    # CONSTRAINTS
    # =====================================================

    def create_constraints(self):

        constraints = [

            """
            CREATE CONSTRAINT document_id
            IF NOT EXISTS
            FOR (n:Document)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT part_id
            IF NOT EXISTS
            FOR (n:Part)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT chapter_id
            IF NOT EXISTS
            FOR (n:Chapter)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT article_id
            IF NOT EXISTS
            FOR (n:Article)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT section_id
            IF NOT EXISTS
            FOR (n:Section)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT clause_id
            IF NOT EXISTS
            FOR (n:Clause)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT subclause_id
            IF NOT EXISTS
            FOR (n:SubClause)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT romanclause_id
            IF NOT EXISTS
            FOR (n:RomanClause)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT proviso_id
            IF NOT EXISTS
            FOR (n:Proviso)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT explanation_id
            IF NOT EXISTS
            FOR (n:Explanation)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT illustration_id
            IF NOT EXISTS
            FOR (n:Illustration)
            REQUIRE n.id IS UNIQUE
            """,

            """
            CREATE CONSTRAINT schedule_id
            IF NOT EXISTS
            FOR (n:Schedule)
            REQUIRE n.id IS UNIQUE
            """
        ]

        for constraint in constraints:
            self.execute(constraint)

    # =====================================================
    # MERGE NODE
    # =====================================================

    def merge_node(
        self,
        label: str,
        node_id: str,
        properties: dict
    ):

        query = f"""
        MERGE (n:{label} {{id:$id}})
        SET n += $properties
        """

        self.execute(
            query,
            {
                "id": node_id,
                "properties": properties
            }
        )

    # =====================================================
    # MERGE RELATIONSHIP
    # =====================================================

    def merge_relationship(
        self,
        source_id: str,
        target_id: str,
        relation: str,
        properties: dict | None = None
    ):

        query = f"""
        MATCH (a {{id:$source_id}})
        MATCH (b {{id:$target_id}})
        MERGE (a)-[r:{relation}]->(b)
        SET r += $properties
        """

        self.execute(
            query,
            {
                "source_id": source_id,
                "target_id": target_id,
                "properties": properties or {}
            }
        )

    # =====================================================
    # GET NODE
    # =====================================================

    def get_node(
        self,
        node_id: str
    ):

        result = self.execute(
            """
            MATCH (n {id:$id})
            RETURN n
            """,
            {
                "id": node_id
            }
        )

        record = result.single()

        if record:

            return dict(
                record["n"]
            )

        return None

    # =====================================================
    # GET NODE + NEIGHBORS
    # =====================================================

    def get_node_with_neighbors(
        self,
        node_id: str
    ):

        query = """
        MATCH (n {id:$id})

        OPTIONAL MATCH (n)-[r]-(m)

        RETURN
            n,
            collect(
                {
                    relation:type(r),
                    neighbor:properties(m)
                }
            ) AS neighbors
        """

        records = self.execute(
            query,
            {"id": node_id}
        )

        if not records:
            return None

        record = records[0]

        return {
            "node": dict(record["n"]),
            "neighbors": record["neighbors"]
        }

    # =====================================================
    # EXPAND GRAPH
    # =====================================================

    def expand(
        self,
        node_id: str,
        depth: int = 2
    ):

        query = """
        MATCH p=(n {id:$id})-[*1..%d]-(m)
        RETURN p
        """ % depth

        result = self.execute(
            query,
            {
                "id": node_id
            }
        )

        return [
            record.data()
            for record in result
        ]

    # =====================================================
    # COUNT NODES
    # =====================================================

    def count_nodes(self):

        return self.execute("MATCH (n) RETURN count(n) AS count")[0]["count"]

    # =====================================================
    # COUNT RELATIONSHIPS
    # =====================================================

    def count_relationships(self):

        return self.execute("MATCH ()-[r]->() RETURN count(r) AS count")[0]["count"]

    # =====================================================
    # LABEL STATS
    # =====================================================

    def label_stats(
        self
    ):

        result = self.execute(
            """
            MATCH (n)

            RETURN
            labels(n)[0] AS label,
            count(*) AS count

            ORDER BY count DESC
            """
        )

        return [
            {
                "label":
                    record["label"],

                "count":
                    record["count"]
            }
            for record in result
        ]

    # =====================================================
    # DOCUMENT STATS
    # =====================================================

    def document_stats(
        self
    ):

        result = self.execute(
            """
            MATCH (n)

            RETURN
            n.document AS document,
            count(*) AS count

            ORDER BY count DESC
            """
        )

        return [
            {
                "document":
                    record["document"],

                "count":
                    record["count"]
            }
            for record in result
        ]

    # =====================================================
    # GET NEIGHBORS
    # =====================================================

    def get_neighbors(
        self,
        node_id: str
    ):

        result = self.execute(
            """
            MATCH (n {id:$id})-[r]-(m)

            RETURN
            type(r) AS relation,
            m.id AS target
            """,
            {
                "id": node_id
            }
        )

        return [
            {
                "relation":
                    record["relation"],

                "target":
                    record["target"]
            }
            for record in result
        ]


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    store = Neo4jStore()

    store.create_constraints()

    store.merge_node(
        label="Document",
        node_id="CONST",
        properties={
            "id": "CONST",
            "document": "CONSTITUTION",
            "node_type": "Document",
            "name": "Constitution of India"
        }
    )

    store.merge_node(
        label="Article",
        node_id="CONST-21",
        properties={
            "id": "CONST-21",
            "document": "CONSTITUTION",
            "node_type": "Article",
            "article_no": "21",
            "title": "Protection of life and personal liberty"
        }
    )

    store.merge_relationship(
        "CONST",
        "CONST-21",
        "HAS_ARTICLE"
    )

    logger.debug('%s %s', "Nodes:", store.count_nodes())

    logger.debug('%s %s', "Relationships:", store.count_relationships())

    logger.debug("%s", store.get_neighbors("CONST"))

    logger.debug('%s', store.label_stats())

    store.close()
