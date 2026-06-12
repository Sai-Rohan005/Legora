from embeddings_test import (
    EmbeddingGenerator
)

from qdrant_store import (
    QdrantStore
)
from constitution_parser import ConstitutionParser
from chunker_test import LegalChunker


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