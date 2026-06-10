from __future__ import annotations

import uuid
from typing import List, Dict, Any


class LegalRecordGenerator:

    def __init__(self):
        pass

    def _id(self):
        return str(uuid.uuid4())

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
                "id": self._id(),

                # keep ONE source of truth
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
    # SMART EMBEDDING BUILDER (IMPROVED)
    # ---------------------------------------------------

    def _build_embedding_text(
        self,
        document_type: str,
        chunk_type: str,
        text: str,
        meta: dict
    ) -> str:

        lines = []

        # -----------------------------
        # DOCUMENT CONTEXT
        # -----------------------------
        lines.append(f"Document: {document_type}")

        # -----------------------------
        # HIERARCHY CONTEXT (ORDERED)
        # -----------------------------
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
            if key in meta and meta[key]:
                lines.append(f"{label}: {meta[key]}")

        # -----------------------------
        # CHUNK TYPE
        # -----------------------------
        lines.append(f"Chunk Type: {chunk_type}")

        # -----------------------------
        # CONTENT
        # -----------------------------
        lines.append("")
        lines.append("Content:")
        lines.append(text.strip())

        return "\n".join(lines).strip()

    # ---------------------------------------------------
    # CLEAN METADATA BUILDER
    # ---------------------------------------------------

    def _build_metadata(
        self,
        document_type: str,
        chunk_type: str,
        meta: dict
    ) -> Dict[str, Any]:

        clean_meta = {}

        # copy only meaningful fields
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

        for k in allowed_keys:
            if k in meta:
                clean_meta[k] = meta[k]

        # system fields
        clean_meta["document_type"] = document_type
        clean_meta["chunk_type"] = chunk_type

        return clean_meta