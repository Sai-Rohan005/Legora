from __future__ import annotations

import uuid
import hashlib
from typing import List, Dict, Any


class LegalRecordGenerator:

    def __init__(self):
        pass

    # ---------------------------------------------------
    # STABLE CHUNK ID (CORE FIX)
    # ---------------------------------------------------
    def _id(self, chunk: dict) -> str:

        # If already assigned externally, trust it
        if chunk.get("id"):
            return chunk["id"]

        meta = chunk.get("meta", {})

        document_uuid = chunk.get("document_uuid")

        # If document UUID exists → deterministic per document
        if document_uuid:
            base = f"{document_uuid}|{chunk.get('type')}|{chunk.get('text')}"

            return str(uuid.uuid5(
                uuid.UUID(document_uuid),
                base
            ))

        # fallback (still deterministic but weaker)
        raw = f"{chunk.get('type')}|{meta}|{chunk.get('text')}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]

    # ---------------------------------------------------
    # MAIN ENTRY
    # ---------------------------------------------------
    def generate(
        self,
        normalized_chunks: List[dict],
        document_type: str
    ) -> List[dict]:

        records = []

        for chunk in normalized_chunks:

            chunk_type = chunk.get("type", "unknown")
            text = chunk.get("text", "")
            meta = chunk.get("meta", {}) or {}

            embedding_text = self._build_embedding_text(
                document_type=document_type,
                chunk_type=chunk_type,
                text=text,
                meta=meta
            )

            records.append({
                # 🔥 SAME ID USED FOR NEO4J + QDRANT
                "id": self._id(chunk),

                "document_type": document_type,
                "chunk_type": chunk_type,
                "embedding_text": embedding_text,

                "metadata": self._build_metadata(
                    document_type,
                    chunk_type,
                    meta
                )
            })

        return records

    # ---------------------------------------------------
    # EMBEDDING BUILDER
    # ---------------------------------------------------
    def _build_embedding_text(
        self,
        document_type: str,
        chunk_type: str,
        text: str,
        meta: dict
    ) -> str:

        lines = [f"Document: {document_type}"]

        hierarchy_keys = [
            ("part_no", "Part"),
            ("division_no", "Division"),
            ("chapter_no", "Chapter"),
            ("provision_no", "Provision"),
            ("section_no", "Section"),
            ("clause_no", "Clause"),
            ("sub_clause_no", "SubClause"),
            ("roman_no", "Roman")
        ]

        for key, label in hierarchy_keys:
            if meta.get(key):
                lines.append(f"{label}: {meta[key]}")

        lines.append(f"Chunk Type: {chunk_type}")
        lines.append("")
        lines.append("Content:")
        lines.append(text.strip())

        return "\n".join(lines).strip()

    # ---------------------------------------------------
    # METADATA CLEANING
    # ---------------------------------------------------
    def _build_metadata(
        self,
        document_type: str,
        chunk_type: str,
        meta: dict
    ) -> Dict[str, Any]:

        allowed_keys = {
            "part_no",
            "division_no",
            "chapter_no",
            "provision_no",
            "section_no",
            "clause_no",
            "sub_clause_no",
            "roman_no",
            "title"
        }

        clean_meta = {
            k: meta[k]
            for k in allowed_keys
            if k in meta
        }

        clean_meta["document_type"] = document_type
        clean_meta["chunk_type"] = chunk_type

        return clean_meta