from __future__ import annotations

# =====================================================
# CONSTITUTION
# =====================================================

from db.parsers.consitution.constitution_parser import (
    ConstitutionParser
)

from db.graph_builders.constitution_graph_builder import (
    ConstitutionGraphBuilder
)

# =====================================================
# BNS
# =====================================================

from db.parsers.bns.cleaner import (
    BNSTextCleaner
)

from db.parsers.bns.bns_parser import (
    BNSParser
)

from db.graph_builders.bns_graph_builder import (
    BNSGraphBuilder
)

# =====================================================
# BNSS
# =====================================================

from db.parsers.bnss.cleaner import (
    BNSSTextCleaner
)

from db.parsers.bnss.bnss_parser import (
    BNSSParser
)

from db.graph_builders.bnss_graph_builder import (
    BNSSGraphBuilder
)

# =====================================================
# BSA
# =====================================================

from db.parsers.bsa.cleaner import (
    BSATextCleaner
)

from db.parsers.bsa.bsa_parser import (
    BSAParser
)

from db.graph_builders.bsa_graph_builder import (
    BSAGraphBuilder
)

# =====================================================
# NEO4J
# =====================================================

from db.neo4j_store import (
    Neo4jStore
)

class AllFilesLoader:
    # =====================================================
    # CONSTITUTION
    # =====================================================
    @staticmethod
    def load_constitution(
        store: Neo4jStore
    ):

        print(
            "\nLoading Constitution..."
        )

        with open(
            "db/pdfs/constitution.txt",
            "r",
            encoding="utf8"
        ) as f:

            text = f.read()

        parser = ConstitutionParser()

        constitution = parser.parse(
            text
        )

        builder = (
            ConstitutionGraphBuilder(
                store
            )
        )

        builder.build(
            constitution
        )

        print(
            "Constitution loaded"
        )


    # =====================================================
    # BNS
    # =====================================================
    @staticmethod
    def load_bns(
        store: Neo4jStore
    ):

        print(
            "\nLoading BNS..."
        )

        with open(
            "db/pdfs/bns.txt",
            "r",
            encoding="utf8"
        ) as f:

            text = f.read()

        cleaner = BNSTextCleaner()

        text = cleaner.clean(
            text
        )

        parser = BNSParser()

        bns = parser.parse(
            text
        )

        builder = (
            BNSGraphBuilder(
                store
            )
        )

        builder.build(
            bns
        )

        print(
            "BNS loaded"
        )


    # =====================================================
    # BNSS
    # =====================================================
    @staticmethod
    def load_bnss(
        store: Neo4jStore
    ):

        print(
            "\nLoading BNSS..."
        )

        with open(
            "db/pdfs/bnss.txt",
            "r",
            encoding="utf8"
        ) as f:

            text = f.read()

        cleaner = (
            BNSSTextCleaner()
        )

        text = cleaner.clean(
            text
        )

        parser = BNSSParser()

        bnss = parser.parse(
            text
        )

        builder = (
            BNSSGraphBuilder(
                store
            )
        )

        builder.build(
            bnss
        )

        print(
            "BNSS loaded"
        )


    # =====================================================
    # BSA
    # =====================================================
    @staticmethod
    def load_bsa(
        store: Neo4jStore
    ):

        print(
            "\nLoading BSA..."
        )

        with open(
            "db/pdfs/bsa.txt",
            "r",
            encoding="utf8"
        ) as f:

            text = f.read()

        cleaner = BSATextCleaner()

        text = cleaner.clean(
            text
        )

        parser = BSAParser()

        bsa = parser.parse(
            text
        )

        builder = (
            BSAGraphBuilder(
                store
            )
        )

        builder.build(
            bsa
        )

        print(
            "BSA loaded"
        )


    # =====================================================
    # MAIN
    # =====================================================

    def main(self):

        store = Neo4jStore(
            uri="bolt://localhost:7687",
            username="neo4j",
            password="test12345"
        )

        # -----------------------------------------
        # Create constraints
        # -----------------------------------------

        store.create_constraints()

        # -----------------------------------------
        # Fresh graph
        # -----------------------------------------

        answer = input(
            "\nClear existing graph? (y/n): "
        )

        if answer.lower() == "y":

            store.clear_graph()

            print(
                "Graph cleared"
            )

            store.create_constraints()

        # -----------------------------------------
        # Load everything
        # -----------------------------------------

        try:
            self.load_constitution(store)
        except Exception as e:
            print(f"Constitution failed: {e}")

        try:
            self.load_bns(store)
        except Exception as e:
            print(f"BNS failed: {e}")

        try:
            self.load_bnss(store)
        except Exception as e:
            print(f"BNSS failed: {e}")

        try:
            self.load_bsa(store)
        except Exception as e:
            print(f"BSA failed: {e}")

        # -----------------------------------------
        # Stats
        # -----------------------------------------

        print(
            "\n================================="
        )

        print(
            "LEGAL KNOWLEDGE GRAPH CREATED"
        )

        print(
            "=================================\n"
        )

        print(
            "Nodes:",
            store.count_nodes()
        )

        print(
            "Relationships:",
            store.count_relationships()
        )

        store.close()

        print(
            "\nDone."
        )


if __name__ == "__main__":
    load=AllFilesLoader()
    load.main()