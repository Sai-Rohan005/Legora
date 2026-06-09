from parser import LegalParser
from graph_db import LegalGraphDB  # your class file
from chunking import ConstitutionChunker  # your chunking function
from embeddings_generator import LegalEmbedder  # your embedding function
from vector_db import QdrantIngestor  # your vector database class
# -----------------------------
# LOAD TEXT FILE
# -----------------------------
with open("./text_extracted_ocr_output.txt", "r", encoding="utf-8") as f:
    text = f.read()


# -----------------------------
# PARSE STRUCTURE
# -----------------------------
parser = LegalParser()
parsed_data = parser.parse(text)


# -----------------------------
# CONNECT TO NEO4J
# -----------------------------
graph = LegalGraphDB(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="test12345"
)


# -----------------------------
# INSERT INTO GRAPH DB
# -----------------------------
graph.insert_structure(parsed_data)


print("✅ Data successfully inserted into Neo4j")




chunker = ConstitutionChunker()
chunks = chunker.chunk(text)

embedder = LegalEmbedder(model_name="all-MiniLM-L6-v2")
embeddings = embedder.embed_texts([c.text for c in chunks])


qdrant = QdrantIngestor()
qdrant.upsert_chunks(chunks, embeddings)


# -----------------------------
# CLOSE CONNECTION
# -----------------------------
graph.close()