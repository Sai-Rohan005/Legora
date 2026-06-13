from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional


# =========================================================
# CHUNK MODEL
# =========================================================

@dataclass
class LegalChunk:

    chunk_id: str

    level: str

    document: str

    chapter_no: Optional[str]

    section_no: Optional[str]

    clause_no: Optional[str]

    sub_clause_no: Optional[str]

    roman_no: Optional[str]

    title: str

    text: str

    enriched_text: str

    parent_id: Optional[str]


# =========================================================
# CHUNKER
# =========================================================

class LegalChunker:

    def __init__(
        self,
        document_name: str = "BNS"
    ):
        self.document_name = document_name

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    def build_context(
        self,
        title: str,
        section_no: str = "",
        clause_no: str = "",
        sub_clause_no: str = "",
        roman_no: str = ""
    ) -> str:

        parts = [
            self.document_name
        ]

        if section_no:
            parts.append(
                f"Section {section_no}"
            )

        if title:
            parts.append(
                title
            )

        if clause_no:
            parts.append(
                f"Clause ({clause_no})"
            )

        if sub_clause_no:
            parts.append(
                f"SubClause ({sub_clause_no})"
            )

        if roman_no:
            parts.append(
                f"Roman Clause ({roman_no})"
            )

        return "\n".join(parts)

    # -----------------------------------------------------
    # Main
    # -----------------------------------------------------

    def chunk_document(
        self,
        document
    ) -> List[LegalChunk]:

        chunks = []

        for chapter in document.chapters:

            for section in chapter.sections:

                section_id = (
                    f"BNS-{section.section_no}"
                )

                title = (
                    getattr(
                        section,
                        "title",
                        ""
                    )
                )

                # =================================
                # SECTION CHUNK
                # =================================

                section_chunk = LegalChunk(
                    chunk_id=section_id,

                    level="section",

                    document="bns",

                    chapter_no=
                        chapter.chapter_no,

                    section_no=
                        section.section_no,

                    clause_no=None,

                    sub_clause_no=None,

                    roman_no=None,

                    title=title,

                    text=section.text,

                    enriched_text=
                        self.build_context(
                            title=title,
                            section_no=
                                section.section_no
                        )
                        + "\n\n"
                        + section.text,

                    parent_id=None
                )

                chunks.append(
                    section_chunk
                )

                # =================================
                # CLAUSES
                # =================================

                for clause in section.clauses:

                    clause_id = (
                        f"{section_id}"
                        f"({clause.clause_no})"
                    )

                    clause_chunk = LegalChunk(

                        chunk_id=
                            clause_id,

                        level=
                            "clause",

                        document=
                            "bns",

                        chapter_no=
                            chapter.chapter_no,

                        section_no=
                            section.section_no,

                        clause_no=
                            clause.clause_no,

                        sub_clause_no=
                            None,

                        roman_no=
                            None,

                        title=
                            title,

                        text=
                            clause.text,

                        enriched_text=
                            self.build_context(
                                title=title,
                                section_no=
                                    section.section_no,
                                clause_no=
                                    clause.clause_no
                            )
                            + "\n\n"
                            + clause.text,

                        parent_id=
                            section_id
                    )

                    chunks.append(
                        clause_chunk
                    )

                    # =============================
                    # SUB CLAUSES
                    # =============================

                    for sub in clause.sub_clauses:

                        sub_id = (
                            f"{clause_id}"
                            f"({sub.sub_clause_no})"
                        )

                        sub_chunk = LegalChunk(

                            chunk_id=
                                sub_id,

                            level=
                                "subclause",

                            document=
                                "bns",

                            chapter_no=
                                chapter.chapter_no,

                            section_no=
                                section.section_no,

                            clause_no=
                                clause.clause_no,

                            sub_clause_no=
                                sub.sub_clause_no,

                            roman_no=
                                None,

                            title=
                                title,

                            text=
                                sub.text,

                            enriched_text=
                                self.build_context(
                                    title=title,
                                    section_no=
                                        section.section_no,
                                    clause_no=
                                        clause.clause_no,
                                    sub_clause_no=
                                        sub.sub_clause_no
                                )
                                + "\n\n"
                                + sub.text,

                            parent_id=
                                clause_id
                        )

                        chunks.append(
                            sub_chunk
                        )

                        # =========================
                        # ROMAN CLAUSES
                        # =========================

                        for roman in sub.roman_clauses:

                            roman_id = (
                                f"{sub_id}"
                                f"({roman.roman_no})"
                            )

                            roman_chunk = LegalChunk(

                                chunk_id=
                                    roman_id,

                                level=
                                    "roman",

                                document=
                                    "bns",

                                chapter_no=
                                    chapter.chapter_no,

                                section_no=
                                    section.section_no,

                                clause_no=
                                    clause.clause_no,

                                sub_clause_no=
                                    sub.sub_clause_no,

                                roman_no=
                                    roman.roman_no,

                                title=
                                    title,

                                text=
                                    roman.text,

                                enriched_text=
                                    self.build_context(
                                        title=title,
                                        section_no=
                                            section.section_no,
                                        clause_no=
                                            clause.clause_no,
                                        sub_clause_no=
                                            sub.sub_clause_no,
                                        roman_no=
                                            roman.roman_no
                                    )
                                    + "\n\n"
                                    + roman.text,

                                parent_id=
                                    sub_id
                            )

                            chunks.append(
                                roman_chunk
                            )

                # =================================
                # EXPLANATIONS
                # =================================

                for explanation in (
                    section.explanations
                ):

                    explanation_id = (
                        f"{section_id}"
                        f"-EXP-"
                        f"{explanation.explanation_no}"
                    )

                    chunk = LegalChunk(

                        chunk_id=
                            explanation_id,

                        level=
                            "explanation",

                        document=
                            "bns",

                        chapter_no=
                            chapter.chapter_no,

                        section_no=
                            section.section_no,

                        clause_no=None,

                        sub_clause_no=None,

                        roman_no=None,

                        title=title,

                        text=
                            explanation.text,

                        enriched_text=
                            self.build_context(
                                title=title,
                                section_no=
                                    section.section_no
                            )
                            + "\n\n"
                            + explanation.text,

                        parent_id=
                            section_id
                    )

                    chunks.append(
                        chunk
                    )

        return chunks


# =========================================================
# EXPORT
# =========================================================

def chunks_to_dicts(
    chunks: List[LegalChunk]
):

    return [
        asdict(chunk)
        for chunk in chunks
    ]