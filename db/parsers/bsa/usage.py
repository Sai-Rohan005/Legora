from collections import Counter

from cleaner import BSATextCleaner

from bsa_parser import (
    BSAParser
)

from chunker import (
    LegalChunker,
    chunks_to_dicts
)

from ingest import (
    LegalIngestionPipeline
)


# =====================================================
# LOAD BSA
# =====================================================

with open(
    "../../pdfs/bsa.txt",
    "r",
    encoding="utf8"
) as f:

    text = f.read()


# =====================================================
# CLEAN
# =====================================================

cleaner = BSATextCleaner()

text = cleaner.clean(
    text
)


# =====================================================
# PARSE
# =====================================================

parser = BSAParser()

document = parser.parse(
    text
)


# =====================================================
# PARSER STATS
# =====================================================

sections = 0
clauses = 0
subclauses = 0
roman_clauses = 0
explanations = 0
illustrations = 0
references = 0

for chapter in document.chapters:

    sections += len(
        chapter.sections
    )

    for section in chapter.sections:

        explanations += len(
            section.explanations
        )

        illustrations += len(
            section.illustrations
        )

        references += len(
            section.references
        )

        clauses += len(
            section.clauses
        )

        for clause in section.clauses:

            subclauses += len(
                clause.sub_clauses
            )

            roman_clauses += len(
                clause.roman_clauses
            )

            for sub in clause.sub_clauses:

                roman_clauses += len(
                    sub.roman_clauses
                )


print("\n========== BSA STATS ==========\n")

print(
    f"Parts: {len(document.parts)}"
)

print(
    f"Chapters: {len(document.chapters)}"
)

print(
    f"Sections: {sections}"
)

print(
    f"Clauses: {clauses}"
)

print(
    f"SubClauses: {subclauses}"
)

print(
    f"Roman Clauses: {roman_clauses}"
)

print(
    f"Explanations: {explanations}"
)

print(
    f"Illustrations: {illustrations}"
)

print(
    f"References: {references}"
)


# =====================================================
# VALIDATION
# =====================================================

errors = parser.validate(
    document
)

print(
    f"\nValidation Errors: {len(errors)}"
)

for error in errors[:50]:

    print(error)


# =====================================================
# CHUNK
# =====================================================

chunker = LegalChunker(
    document_name="BSA"
)

chunks = chunks_to_dicts(
    chunker.chunk_document(
        document
    )
)


# =====================================================
# CHUNK STATS
# =====================================================

print(
    "\n========== CHUNK STATS ==========\n"
)

print(
    f"Total Chunks: {len(chunks)}"
)

levels = Counter(
    chunk["level"]
    for chunk in chunks
)

for level, count in sorted(
    levels.items()
):

    print(
        f"{level}: {count}"
    )


# =====================================================
# INGEST
# =====================================================

pipeline = (
    LegalIngestionPipeline(
        collection_name="bsa"
    )
)

pipeline.ingest(
    chunks=chunks,
    batch_size=64,
    recreate_collection=True
)


print(
    "\nBSA successfully indexed."
)