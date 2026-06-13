from collections import Counter

from cleaner import BNSSTextCleaner

from bnss_parser import (
    BNSSParser
)

from chunk_temp import (
    LegalChunker,
    chunks_to_dicts
)

from ingest import (
    LegalIngestionPipeline
)

# =====================================================
# CONFIG
# =====================================================

DOCUMENT_NAME = "BNSS"

COLLECTION_NAME = "bnss"

PDF_PATH = "../../pdfs/bnss.txt"

# =====================================================
# LOAD
# =====================================================

with open(
    PDF_PATH,
    "r",
    encoding="utf8"
) as f:

    text = f.read()

# =====================================================
# CLEAN
# =====================================================

cleaner = BNSSTextCleaner()

text = cleaner.clean(
    text
)

# =====================================================
# PARSE
# =====================================================

parser = BNSSParser()

document = parser.parse(
    text
)

# =====================================================
# CHUNK
# =====================================================

chunker = LegalChunker(
    document_name=DOCUMENT_NAME
)

chunks = chunks_to_dicts(
    chunker.chunk_document(
        document
    )
)

# =====================================================
# STATS
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

pipeline = LegalIngestionPipeline(
    collection_name=
        COLLECTION_NAME
)

pipeline.ingest(
    chunks=
        chunks,

    batch_size=
        64,

    recreate_collection=
        True
)

print(
    f"\n{DOCUMENT_NAME} successfully indexed."
)