# # from Crypto.PublicKey import RSA
# # from Crypto.Hash import SHA256
# # from Crypto.Signature import pss


# # # ----------------------------
# # # 1. Generate RSA Key Pair
# # # ----------------------------
# # def generate_rsa_keys(bits=2048):
# #     key = RSA.generate(bits)

# #     private_key = key.export_key()
# #     public_key = key.publickey().export_key()

# #     return private_key, public_key


# # # ----------------------------
# # # 2. Save Keys to Files
# # # ----------------------------
# # def save_key(key_data, filename):
# #     with open(filename, "wb") as f:
# #         f.write(key_data)


# # # ----------------------------
# # # 3. Load Private Key
# # # ----------------------------
# # def load_private_key(filename="private.pem"):
# #     with open(filename, "rb") as f:
# #         return RSA.import_key(f.read())


# # # ----------------------------
# # # 4. Load Public Key
# # # ----------------------------
# # def load_public_key(filename="public.pem"):
# #     with open(filename, "rb") as f:
# #         return RSA.import_key(f.read())


# # # ----------------------------
# # # 5. Sign Message (RSA-PSS)
# # # ----------------------------
# # def sign_message(message, private_key):
# #     if isinstance(message, str):
# #         message = message.encode("utf-8")

# #     hash_obj = SHA256.new(message)
# #     signature = pss.new(private_key).sign(hash_obj)

# #     return signature


# # # ----------------------------
# # # 6. Verify Signature
# # # ----------------------------
# # def verify_signature(message, signature, public_key):
# #     if isinstance(message, str):
# #         message = message.encode("utf-8")

# #     hash_obj = SHA256.new(message)

# #     try:
# #         pss.new(public_key).verify(hash_obj, signature)
# #         return True
# #     except (ValueError, TypeError):
# #         return False


# # # ----------------------------
# # # 7. Example Usage
# # # ----------------------------
# # if __name__ == "__main__":

# #     # Generate keys
# #     private_key, public_key = generate_rsa_keys()

# #     # Save keys
# #     save_key(private_key, "private.pem")
# #     save_key(public_key, "public.pem")

# #     # Load keys
# #     priv = load_private_key("private.pem")
# #     pub = load_public_key("public.pem")

# #     # Message
# #     msg = "This is a legal RAG secure request"

# #     # Sign
# #     signature = sign_message(msg, priv)
# #     print("Signature generated:", signature.hex())

# #     # Verify
# #     is_valid = verify_signature(msg, signature, pub)
# #     print("Signature valid?", is_valid)


# import requests
# import os
# from dotenv import load_dotenv

# load_dotenv()

# API_TOKEN = os.getenv("kanoon_token")

# BASE_URL = "https://api.indiankanoon.org/search/"


# def search(query):
#     headers = {
#         "Authorization": f"Token {API_TOKEN}",
#         "Content-Type": "application/x-www-form-urlencoded"
#     }

#     data = {
#         "formInput": query
#     }

#     response = requests.post(BASE_URL, headers=headers, data=data)

#     print("STATUS:", response.status_code)
#     print("RESPONSE:", response.text)

#     try:
#         return response.json()
#     except:
#         return response.text


# print(search('"fundamental rights"'))




# from neo4j import GraphDatabase

# driver = GraphDatabase.driver(
#     "bolt://localhost:7687",
#     auth=("neo4j", "test12345")
# )

# with driver.session() as session:
#     query = """
#     MATCH (a:Article {number: 14})
#     RETURN a.text AS content
#     """

#     result = session.run(query)
#     print(result.single())

# driver.close()
# from embeddings_generator import LegalEmbedder
# from vector_db import QdrantIngestor

# question = "what does article 14 of the indian constitution say?"

# # Create embedding

# embedder = LegalEmbedder(model_name="all-MiniLM-L6-v2")
# embedding = embedder.embed_texts(question)

# # Search Qdrant

# qdrant = QdrantIngestor()
# hits = qdrant.search(
#     # collection_name="legal_constitution",
#     query_vector=embedding.tolist()[0],
#     limit=5
# )

# # article_ids = [hit.payload["article_id"] for hit in hits]
# print("Top matching article IDs:", hits)

# # # Fetch from Neo4j
# # query = """
# # MATCH (a:Article)
# # WHERE a.article_id IN $ids
# # RETURN a.article_id, a.text
# # """

# # result = session.run(query, ids=article_ids)

# # for row in result:
#     # print(row["a.text"])



# from parser import ConstitutionParser
# from record_generator import ConstitutionRecordGenerator

# with open("text_extracted_ocr_output.txt", "r", encoding="utf8") as f:
#         text = f.read()

# parser = ConstitutionParser()
# parts = parser.parse(text)

# generator = ConstitutionRecordGenerator()

# records = generator.generate(parts)

# print("Total Records:", len(records))

# print(records[0])






from __future__ import annotations

from db.neo4j_store import Neo4jStore


class BNSGraphBuilder:

    DOCUMENT_ID = "BNS"

    def __init__(self, store: Neo4jStore):
        self.store = store

    # =====================================================
    # NODE FACTORY
    # =====================================================

    def _props(self, node_id: str, node_type: str, **kwargs):
        return {
            "id": node_id,
            "document": "BNS",
            "node_type": node_type,
            **kwargs
        }

    # =====================================================
    # BUILD ENTRY
    # =====================================================

    def build(self, bns):

        self._create_document()

        if getattr(bns, "parts", []):
            self._build_parts(bns)
        else:
            self._build_chapters(bns.chapters, self.DOCUMENT_ID)

    # =====================================================
    # DOCUMENT
    # =====================================================

    def _create_document(self):

        self.store.merge_node(
            label="Document",
            node_id=self.DOCUMENT_ID,
            properties=self._props(
                self.DOCUMENT_ID,
                "Document",
                name="Bharatiya Nyaya Sanhita, 2023"
            )
        )

    # =====================================================
    # PARTS
    # =====================================================

    def _build_parts(self, bns):

        for part in bns.parts:

            part_id = f"BNS-PART-{part.part_no}"

            self.store.merge_node(
                label="Part",
                node_id=part_id,
                properties=self._props(
                    part_id,
                    "Part",
                    part_no=part.part_no,
                    title=part.title,
                    text=part.text
                )
            )

            # Document → Part
            self.store.merge_relationship(
                self.DOCUMENT_ID,
                part_id,
                "HAS_PART"
            )

            self._build_chapters(part.chapters, part_id)

    # =====================================================
    # CHAPTERS
    # =====================================================

    def _build_chapters(self, chapters, parent_id):

        for chapter in chapters:

            chapter_id = f"BNS-CH-{chapter.chapter_no}"

            self.store.merge_node(
                label="Chapter",
                node_id=chapter_id,
                properties=self._props(
                    chapter_id,
                    "Chapter",
                    chapter_no=chapter.chapter_no,
                    title=chapter.chapter_title,
                    text=chapter.text
                )
            )

            # Parent → Child (IMPORTANT for retrieval)
            self.store.merge_relationship(
                parent_id,
                chapter_id,
                "HAS_CHAPTER"
            )

            self._build_sections(chapter.sections, chapter_id)

    # =====================================================
    # SECTIONS
    # =====================================================

    def _build_sections(self, sections, chapter_id):

        for section in sections:

            section_id = f"BNS-{section.section_no}"

            self.store.merge_node(
                label="Section",
                node_id=section_id,
                properties=self._props(
                    section_id,
                    "Section",
                    section_no=section.section_no,
                    title=section.section_title,
                    text=section.text
                )
            )

            # Parent → Child (CRITICAL FIX)
            self.store.merge_relationship(
                chapter_id,
                section_id,
                "HAS_SECTION"
            )

            # Optional reverse link (useful for normalization)
            self.store.merge_relationship(
                section_id,
                chapter_id,
                "BELONGS_TO"
            )

            self._build_clauses(section, section_id)
            self._build_explanations(section, section_id)
            self._build_illustrations(section, section_id)
            self._build_references(section, section_id)

    # =====================================================
    # CLAUSES
    # =====================================================

    def _build_clauses(self, section, section_id):

        for clause in getattr(section, "clauses", []):

            clause_id = f"{section_id}({clause.clause_no})"

            self.store.merge_node(
                label="Clause",
                node_id=clause_id,
                properties=self._props(
                    clause_id,
                    "Clause",
                    clause_no=clause.clause_no,
                    text=clause.text
                )
            )

            self.store.merge_relationship(
                section_id,
                clause_id,
                "HAS_CLAUSE"
            )

            self.store.merge_relationship(
                clause_id,
                section_id,
                "BELONGS_TO"
            )

            self._build_subclauses(clause, clause_id)

    # =====================================================
    # SUBCLAUSES
    # =====================================================

    def _build_subclauses(self, clause, clause_id):

        for sub in getattr(clause, "sub_clauses", []):

            sub_id = f"{clause_id}({sub.sub_clause_no})"

            self.store.merge_node(
                label="SubClause",
                node_id=sub_id,
                properties=self._props(
                    sub_id,
                    "SubClause",
                    sub_clause_no=sub.sub_clause_no,
                    text=sub.text
                )
            )

            self.store.merge_relationship(
                clause_id,
                sub_id,
                "HAS_SUBCLAUSE"
            )

            self.store.merge_relationship(
                sub_id,
                clause_id,
                "BELONGS_TO"
            )

            self._build_roman_clauses(sub, sub_id)

    # =====================================================
    # ROMAN CLAUSES
    # =====================================================

    def _build_roman_clauses(self, sub, sub_id):

        for roman in getattr(sub, "roman_clauses", []):

            roman_id = f"{sub_id}({roman.roman_no})"

            self.store.merge_node(
                label="RomanClause",
                node_id=roman_id,
                properties=self._props(
                    roman_id,
                    "RomanClause",
                    roman_no=roman.roman_no,
                    text=roman.text
                )
            )

            self.store.merge_relationship(
                sub_id,
                roman_id,
                "HAS_ROMANCLAUSE"
            )

            self.store.merge_relationship(
                roman_id,
                sub_id,
                "BELONGS_TO"
            )

    # =====================================================
    # EXPLANATIONS
    # =====================================================

    def _build_explanations(self, section, section_id):

        for idx, explanation in enumerate(
            getattr(section, "explanations", []),
            start=1
        ):

            explanation_id = f"{section_id}-EXPL-{idx}"

            self.store.merge_node(
                label="Explanation",
                node_id=explanation_id,
                properties=self._props(
                    explanation_id,
                    "Explanation",
                    text=explanation.text
                )
            )

            self.store.merge_relationship(
                section_id,
                explanation_id,
                "HAS_EXPLANATION"
            )

            self.store.merge_relationship(
                explanation_id,
                section_id,
                "BELONGS_TO"
            )

    # =====================================================
    # ILLUSTRATIONS
    # =====================================================

    def _build_illustrations(self, section, section_id):

        for idx, illustration in enumerate(
            getattr(section, "illustrations", []),
            start=1
        ):

            illustration_id = f"{section_id}-ILL-{idx}"

            self.store.merge_node(
                label="Illustration",
                node_id=illustration_id,
                properties=self._props(
                    illustration_id,
                    "Illustration",
                    illustration_no=getattr(illustration, "illustration_no", None),
                    text=illustration.text
                )
            )

            self.store.merge_relationship(
                section_id,
                illustration_id,
                "HAS_ILLUSTRATION"
            )

            self.store.merge_relationship(
                illustration_id,
                section_id,
                "BELONGS_TO"
            )

    # =====================================================
    # REFERENCES
    # =====================================================

    def _build_references(self, section, section_id):

        for ref in getattr(section, "references", []):

            target_section = getattr(ref, "section_no", None)

            if not target_section:
                continue

            target_id = f"BNS-{target_section}"

            self.store.merge_relationship(
                section_id,
                target_id,
                "REFERENCES"
            )