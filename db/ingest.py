# from parser import ConstitutionParser  # your parser class
# from graph_db import LegalGraphDB  # your class file
# from chunking import ConstitutionChunker  # your chunking function
# from embeddings_generator import LegalEmbedder  # your embedding function
# from vector_db import QdrantIngestor  # your vector database class
# from record_generator import ConstitutionRecordGenerator  # your record generator
# # -----------------------------
# # LOAD TEXT FILE
# # -----------------------------
# with open("./text_extracted_ocr_output.txt", "r", encoding="utf-8") as f:
#     text = f.read()


# # -----------------------------
# # PARSE STRUCTURE
# # -----------------------------
# parser = ConstitutionParser()
# parsed_data = parser.parse(text)


# # -----------------------------
# # CONNECT TO NEO4J
# # -----------------------------
# graph = LegalGraphDB(
#     uri="bolt://localhost:7687",
#     user="neo4j",
#     password="test12345"
# )


# # -----------------------------
# # INSERT INTO GRAPH DB
# # -----------------------------
# graph.insert_structure(parsed_data)


# print("✅ Data successfully inserted into Neo4j")




# record_gen = ConstitutionRecordGenerator()
# records = record_gen.generate(parsed_data)
# texts = [
#     record["embedding_text"]
#     for record in records
# ]


# embedder = LegalEmbedder(model_name="BAAI/bge-large-en-v1.5")
# embeddings = embedder.embed_texts(texts)


# qdrant = QdrantIngestor()
# qdrant.upsert_chunks(records, embeddings)


# # -----------------------------
# # CLOSE CONNECTION
# # -----------------------------
# graph.close()

from parsers.constitution_parser import ConstitutionParser
from parsers.bns_parser import BNSParser
from parsers.bnss_parser import BNSSParser
from parsers.bsa_parser import BSAParser
from parsers.legal_normaliser import LegalNormalizer
from generator.legal_record_generator import LegalRecordGenerator


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

#  print(contituion_parsed)
# print(bns_parsed.divisions[0])
# print(bnss_parsed[0])
# print(bsa_parsed)

normaliser = LegalNormalizer()
constitution_normalised = normaliser.normalize(
    contituion_parsed,
    document_type="constitution"
)
# print(constitution_normalised)
bns_normalised = normaliser.normalize(
    bns_parsed.divisions,
    document_type="bns"
)
# print(bns_normalised.divisions[0])
bnss_normalised = normaliser.normalize(
    bnss_parsed,
    document_type="bnss"
)
# print(bnss_normalised.divisions[0])

# list_of_normalised = [
#     constitution_normalised,
#     bns_normalised,
#     bnss_normalised,
#     bsa_parsed
# ]

# dic = {}

# for item in list_of_normalised:
#     t = type(item)
#     dic[t] = dic.get(t, 0) + 1

# print(dic)



from generator.get_all_chunks import normalise_document
all_chunks = []

for doc in [
    constitution_normalised,
    bns_normalised,
    bnss_normalised,
    bsa_parsed
]:
    all_chunks.extend(normalise_document(doc))

# # print(len(all_chunks))
# print(all_chunks[:3])














record_generator = LegalRecordGenerator()
records = record_generator.generate(
    normalized_chunks=all_chunks,
    document_type="legal"
) 

print(f"✅ Generated {len(records)} records ready for embedding and ingestion into Qdrant")
print(f"Sample record: {records[0]}")
