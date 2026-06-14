from __future__ import annotations

# =====================================================
# BNS
# =====================================================

from db.parsers.bns.cleaner import (
    BNSTextCleaner
)

from db.parsers.bns.bns_parser import (
    BNSParser
)

from db.parsers.bns.chunker import (
    LegalChunker as BNSChunker,
    chunks_to_dicts as bns_to_dicts
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

from db.parsers.bnss.chunker import (
    LegalChunker as BNSSChunker,
    chunks_to_dicts as bnss_to_dicts
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

from db.parsers.bsa.chunker import (
    LegalChunker as BSAChunker,
    chunks_to_dicts as bsa_to_dicts
)

# =====================================================
# CONSTITUTION
# =====================================================

from db.parsers.consitution.cleaner import (
    ConstitutionTextCleaner
)

from db.parsers.consitution.constitution_parser import (
    ConstitutionParser
)

from db.parsers.consitution.chunker import (
    LegalChunker as ConstitutionChunker,
    chunks_to_dicts as constitution_to_dicts
)


class LegalCorpusBuilder:

    # =================================================
    # LOAD FILE
    # =================================================

    @staticmethod
    def load_text(
        filepath
    ):

        with open(
            filepath,
            "r",
            encoding="utf8"
        ) as f:

            return f.read()

    # =================================================
    # BNS
    # =================================================

    def build_bns_chunks(
        self,
        filepath
    ):

        text = self.load_text(
            filepath
        )

        text = (
            BNSTextCleaner()
            .clean(text)
        )

        document = (
            BNSParser()
            .parse(text)
        )

        chunks = (
            BNSChunker(
                document_name="BNS"
            )
            .chunk_document(
                document
            )
        )

        return (
            bns_to_dicts(
                chunks
            )
        )

    # =================================================
    # BNSS
    # =================================================

    def build_bnss_chunks(
        self,
        filepath
    ):

        text = self.load_text(
            filepath
        )

        text = (
            BNSSTextCleaner()
            .clean(text)
        )

        document = (
            BNSSParser()
            .parse(text)
        )

        chunks = (
            BNSSChunker(
                document_name="BNSS"
            )
            .chunk_document(
                document
            )
        )

        return (
            bnss_to_dicts(
                chunks
            )
        )

    # =================================================
    # BSA
    # =================================================

    def build_bsa_chunks(
        self,
        filepath
    ):

        text = self.load_text(
            filepath
        )

        text = (
            BSATextCleaner()
            .clean(text)
        )

        document = (
            BSAParser()
            .parse(text)
        )

        chunks = (
            BSAChunker(
                document_name="BSA"
            )
            .chunk_document(
                document
            )
        )

        return (
            bsa_to_dicts(
                chunks
            )
        )

    # =================================================
    # CONSTITUTION
    # =================================================

    def build_constitution_chunks(
        self,
        filepath
    ):

        text = self.load_text(
            filepath
        )

        text = (
            ConstitutionTextCleaner()
            .clean(text)
        )

        document = (
            ConstitutionParser()
            .parse(text)
        )

        chunker = ConstitutionChunker()

        chunks = (
            chunker.chunk_constitution(
                document
            )
        )

        return (
            constitution_to_dicts(
                chunks
            )
        )

    # =================================================
    # ALL CHUNKS
    # =================================================

    def build_all_chunks(
        self,
        bns_path,
        bnss_path,
        bsa_path,
        constitution_path
    ):

        all_chunks = []

        print(
            "\nBuilding BNS..."
        )

        all_chunks.extend(
            self.build_bns_chunks(
                bns_path
            )
        )

        print(
            "Building BNSS..."
        )

        all_chunks.extend(
            self.build_bnss_chunks(
                bnss_path
            )
        )

        print(
            "Building BSA..."
        )

        all_chunks.extend(
            self.build_bsa_chunks(
                bsa_path
            )
        )

        print(
            "Building Constitution..."
        )

        all_chunks.extend(
            self.build_constitution_chunks(
                constitution_path
            )
        )

        return all_chunks


# =====================================================
# TEST
# =====================================================

if __name__ == "__main__":

    builder = (
        LegalCorpusBuilder()
    )

    all_chunks = (
        builder.build_all_chunks(
            bns_path=
                "db/pdfs/bns.txt",

            bnss_path=
                "db/pdfs/bnss.txt",

            bsa_path=
                "db/pdfs/bsa.txt",

            constitution_path=
                "db/pdfs/constitution.txt"
        )
    )

    print()

    print(
        f"Total Chunks: "
        f"{len(all_chunks)}"
    ) 