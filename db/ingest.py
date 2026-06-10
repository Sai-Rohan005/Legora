

from email.utils import parsedate

from embeddings_generator import LegalEmbedder
from graph_db import LegalGraphDB
from vector_db import QdrantIngestor
from parsers.constitution_parser import ConstitutionParser
from parsers.bns_parser import BNSParser
from parsers.bnss_parser import BNSSParser
from parsers.bsa_parser import BSAParser
from parsers.legal_normaliser import LegalNormalizer
from generator.legal_record_generator import LegalRecordGenerator
from generator.get_all_chunks import normalise_document


with open("./pdfs/constitution.txt", "r", encoding="utf-8") as f:
    constitution_text = f.read()
with open("./pdfs/bns.txt", "r", encoding="utf-8") as f:
    bns_text = f.read()
with open("./pdfs/bnss.txt", "r", encoding="utf-8") as f:
    bnss_text = f.read()
with open("./pdfs/bsa.txt", "r", encoding="utf-8") as f:
    bsa_text = f.read()

constitution_parser = ConstitutionParser()
bns_parser = BNSParser()
bnss_parser = BNSSParser()
bsa_parser = BSAParser()

contituion_parsed = constitution_parser.parse(constitution_text)
bns_parsed = bns_parser.parse(bns_text)
bnss_parsed = bnss_parser.parse(bnss_text)
bsa_parsed = bsa_parser.parse(bsa_text)



normaliser = LegalNormalizer()
constitution_normalised = normaliser.normalize(
    contituion_parsed,
    document_type="constitution"
)
bns_normalised = normaliser.normalize(
    bns_parsed.divisions,
    document_type="bns"
)
bnss_normalised = normaliser.normalize(
    bnss_parsed,
    document_type="bnss"
)

all_chunks = []

for doc in [
    constitution_normalised,
    bns_normalised,
    bnss_normalised,
    bsa_parsed
]:
    all_chunks.extend(normalise_document(doc))



record_generator = LegalRecordGenerator()
records = record_generator.generate(
    normalized_chunks=all_chunks,
    document_type="legal"
) 


# -----------------------------
# EMBEDDINGS
# -----------------------------

embedder = LegalEmbedder(model_name="BAAI/bge-large-en-v1.5")


records = embedder.embed_records(records)   # ✅ ONLY records


# -----------------------------
# GRAPH DB (Neo4j)
# -----------------------------

graph = LegalGraphDB(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="test12345"
)

graph.insert_chunks(records)
print("✅ Data inserted into Neo4j")


# -----------------------------
# VECTOR DB (Qdrant)
# -----------------------------

qdrant = QdrantIngestor()
qdrant.upsert_chunks(records)   # ✅ ONLY records

print("✅ Data inserted into Qdrant")


# -----------------------------
# CLOSE
# -----------------------------
graph.close()