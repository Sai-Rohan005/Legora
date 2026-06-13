from collections import Counter

from cleaner import BNSTextCleaner
from bns_parser import BNSParser

from chunk_temp import (
    LegalChunker,
    chunks_to_dicts
)

from ingest import (
    LegalIngestionPipeline
)

# =====================================================
# LOAD BNS
# =====================================================

with open(
    "../../pdfs/bns.txt",
    "r",
    encoding="utf8"
) as f:

    text = f.read()

# =====================================================
# CLEAN
# =====================================================

cleaner = BNSTextCleaner()

text = cleaner.clean(
    text
)

# =====================================================
# PARSE
# =====================================================

parser = BNSParser()

document = parser.parse(
    text
)

# =====================================================
# CHUNK
# =====================================================

chunker = LegalChunker()

chunks = chunks_to_dicts(
    chunker.chunk_document(
        document
    )
)

# =====================================================
# STATS
# =====================================================

print("\n========== CHUNK STATS ==========\n")

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
    LegalIngestionPipeline()
)

# Optional:
# wipe collection before indexing

try:

    pipeline.store.client.delete_collection(
        collection_name="bns"
    )

    print(
        "\nDeleted existing collection."
    )

except Exception:
    pass

pipeline.ingest(
    chunks=chunks,
    batch_size=64
)

print(
    "\nBNS successfully indexed."
)