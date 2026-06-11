import uuid

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


# --------------------------------------------------
# LOAD RAW TEXT
# --------------------------------------------------

with open("./pdfs/constitution.txt", "r", encoding="utf-8") as f:
    constitution_text = f.read()

with open("./pdfs/bns.txt", "r", encoding="utf-8") as f:
    bns_text = f.read()

with open("./pdfs/bnss.txt", "r", encoding="utf-8") as f:
    bnss_text = f.read()

with open("./pdfs/bsa.txt", "r", encoding="utf-8") as f:
    bsa_text = f.read()


# --------------------------------------------------
# PARSERS
# --------------------------------------------------

constitution_parser = ConstitutionParser()
bns_parser = BNSParser()
bnss_parser = BNSSParser()
bsa_parser = BSAParser()

contituion_parsed = constitution_parser.parse(constitution_text)
bns_parsed = bns_parser.parse(bns_text)
bnss_parsed = bnss_parser.parse(bnss_text)
bsa_parsed = bsa_parser.parse(bsa_text)


# --------------------------------------------------
# NORMALISE
# --------------------------------------------------

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


# --------------------------------------------------
# FLATTEN ALL CHUNKS
# --------------------------------------------------

all_chunks = []

for doc in [
    constitution_normalised,
    bns_normalised,
    bnss_normalised,
    bsa_parsed
]:
    all_chunks.extend(normalise_document(doc))


# --------------------------------------------------
# ⭐ GLOBAL ID FIX (CRITICAL)
# --------------------------------------------------

for chunk in all_chunks:
    chunk_id = f"{chunk['type']}|" \
               f"{chunk.get('meta', {}).get('division_no','')}-" \
               f"{chunk.get('meta', {}).get('provision_no','')}-" \
               f"{chunk.get('meta', {}).get('clause_no','')}-" \
               f"{hash(chunk['text'])}"

    chunk["id"] = str(chunk_id)


# --------------------------------------------------
# GRAPH DB (NEO4J)
# --------------------------------------------------

graph = LegalGraphDB(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="test12345"
)

graph.insert_chunks(all_chunks)
print("✅ Data inserted into Neo4j")


# --------------------------------------------------
# RECORD GENERATION (FOR VECTOR DB)
# --------------------------------------------------

record_generator = LegalRecordGenerator()

records = record_generator.generate(
    normalized_chunks=all_chunks,
    document_type="legal"
)


# --------------------------------------------------
# EMBEDDINGS
# --------------------------------------------------

embedder = LegalEmbedder(model_name="BAAI/bge-large-en-v1.5")

records = embedder.embed_records(records)


# --------------------------------------------------
# VECTOR DB (QDRANT)
# --------------------------------------------------

qdrant = QdrantIngestor()

qdrant.upsert_chunks(records)

print("✅ Data inserted into Qdrant")


# --------------------------------------------------
# CLEANUP
# --------------------------------------------------

graph.close()