from __future__ import annotations

from db.all_chunks import (
    LegalCorpusBuilder
)

from db.ingest import (
    LegalIngestionPipeline
)
from db.graph_builders.all_loader import AllFilesLoader


def main():
    print("Inserting into neo4j")
    loader=AllFilesLoader()
    loader.main()

    print(
        "\nBuilding Legal Corpus...\n"
    )

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

    print(
        f"\nTotal Chunks: "
        f"{len(all_chunks)}"
    )

    # =====================================
    # SAMPLE
    # =====================================

    print(
        "\nSample Chunk:\n"
    )

    print(
        all_chunks[0]
    )

    # =====================================
    # INGEST
    # =====================================

    pipeline = (
        LegalIngestionPipeline(
            collection_name=
                "legal_rag"
        )
    )

    pipeline.ingest(
        chunks=
            all_chunks,

        recreate_collection=
            True
    )

    print(
        "\nFinished."
    )


if __name__ == "__main__":

    main()