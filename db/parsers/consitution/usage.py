from db.parsers.consitution.embeddings_test import (
    EmbeddingGenerator
)

from db.parsers.consitution.qdrant_store import (
    QdrantStore
)
from db.parsers.consitution.constitution_parser import ConstitutionParser
from db.parsers.consitution.chunker import LegalChunker


with open(
        "../../pdfs/constitution.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()


parser = ConstitutionParser()

constitution = parser.parse(text)


chunker = LegalChunker()

chunks = chunker.chunk_constitution(constitution)

generator = EmbeddingGenerator()

embeddings = generator.generate(
    chunks
)

store = QdrantStore(
    collection_name=
        "constitution"
)

store.create_collection(
    vector_size=
        embeddings.shape[1]
)

store.insert_chunks(
    chunks,
    embeddings
)