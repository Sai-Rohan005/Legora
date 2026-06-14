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
    chapter_title: Optional[str]

    section_no: Optional[str]

    clause_no: Optional[str]

    sub_clause_no: Optional[str]

    roman_no: Optional[str]

    title: str

    text: str

    enriched_text: str

    parent_id: Optional[str]

    root_section_id: Optional[str]

    path: Optional[str]


# =========================================================
# CHUNKER
# =========================================================

class LegalChunker:

    def __init__(
        self,
        document_name: str = "BNSS"
    ):
        self.document_name = document_name

    # -----------------------------------------------------
    # Helpers
    # -----------------------------------------------------

    def build_context(
        self,
        document: str,
        chapter_no: str = "",
        chapter_title: str = "",
        section_no: str = "",
        title: str = "",
        clause_no: str = "",
        sub_clause_no: str = "",
        roman_no: str = ""
    ) -> str:

        parts = [document.upper()]

        if chapter_no:
            parts.append(
                f"Chapter {chapter_no}"
            )

        if chapter_title:
            parts.append(
                chapter_title
            )

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

        document_name = getattr(
            document,
            "document",
            self.document_name
        ).upper()

        for chapter in document.chapters:

            chapter_title = getattr(
                chapter,
                "title",
                ""
            )

            for section in chapter.sections:

                section_id = (
                    f"{document_name}-"
                    f"{section.section_no}"
                )

                section_path = (
                    section_id
                )

                title = getattr(
                    section,
                    "title",
                    ""
                )

                # =================================
                # SECTION
                # =================================

                chunks.append(

                    LegalChunk(

                        chunk_id=
                            section_id,

                        level=
                            "section",

                        document=
                            document_name.lower(),

                        chapter_no=
                            chapter.chapter_no,

                        chapter_title=
                            chapter_title,

                        section_no=
                            section.section_no,

                        clause_no=
                            None,

                        sub_clause_no=
                            None,

                        roman_no=
                            None,

                        title=
                            title,

                        text=
                            section.text,

                        enriched_text=
                            self.build_context(
                                document=
                                    document_name,

                                chapter_no=
                                    chapter.chapter_no,

                                chapter_title=
                                    chapter_title,

                                section_no=
                                    section.section_no,

                                title=
                                    title
                            )
                            + "\n\n"
                            + section.text,

                        parent_id=
                            None,

                        root_section_id=
                            section_id,

                        path=
                            section_path
                    )
                )

                # =================================
                # CLAUSES
                # =================================

                for clause in section.clauses:

                    clause_id = (
                        f"{section_id}"
                        f"({clause.clause_no})"
                    )

                    clause_path = (
                        f"{section_path}"
                        f" > Clause({clause.clause_no})"
                    )

                    chunks.append(

                        LegalChunk(

                            chunk_id=
                                clause_id,

                            level=
                                "clause",

                            document=
                                document_name.lower(),

                            chapter_no=
                                chapter.chapter_no,

                            chapter_title=
                                chapter_title,

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
                                    document=
                                        document_name,

                                    chapter_no=
                                        chapter.chapter_no,

                                    chapter_title=
                                        chapter_title,

                                    section_no=
                                        section.section_no,

                                    title=
                                        title,

                                    clause_no=
                                        clause.clause_no
                                )
                                + "\n\n"
                                + clause.text,

                            parent_id=
                                section_id,

                            root_section_id=
                                section_id,

                            path=
                                clause_path
                        )
                    )

                    # =============================
                    # SUB CLAUSES
                    # =============================

                    for sub in clause.sub_clauses:

                        sub_id = (
                            f"{clause_id}"
                            f"({sub.sub_clause_no})"
                        )

                        sub_path = (
                            f"{clause_path}"
                            f" > SubClause({sub.sub_clause_no})"
                        )

                        chunks.append(

                            LegalChunk(

                                chunk_id=
                                    sub_id,

                                level=
                                    "subclause",

                                document=
                                    document_name.lower(),

                                chapter_no=
                                    chapter.chapter_no,

                                chapter_title=
                                    chapter_title,

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
                                        document=
                                            document_name,

                                        chapter_no=
                                            chapter.chapter_no,

                                        chapter_title=
                                            chapter_title,

                                        section_no=
                                            section.section_no,

                                        title=
                                            title,

                                        clause_no=
                                            clause.clause_no,

                                        sub_clause_no=
                                            sub.sub_clause_no
                                    )
                                    + "\n\n"
                                    + sub.text,

                                parent_id=
                                    clause_id,

                                root_section_id=
                                    section_id,

                                path=
                                    sub_path
                            )
                        )

                        # =========================
                        # ROMAN CLAUSES
                        # =========================

                        for roman in sub.roman_clauses:

                            roman_id = (
                                f"{sub_id}"
                                f"({roman.roman_no})"
                            )

                            roman_path = (
                                f"{sub_path}"
                                f" > Roman({roman.roman_no})"
                            )

                            chunks.append(

                                LegalChunk(

                                    chunk_id=
                                        roman_id,

                                    level=
                                        "roman",

                                    document=
                                        document_name.lower(),

                                    chapter_no=
                                        chapter.chapter_no,

                                    chapter_title=
                                        chapter_title,

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
                                            document=
                                                document_name,

                                            chapter_no=
                                                chapter.chapter_no,

                                            chapter_title=
                                                chapter_title,

                                            section_no=
                                                section.section_no,

                                            title=
                                                title,

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
                                        sub_id,

                                    root_section_id=
                                        section_id,

                                    path=
                                        roman_path
                                )
                            )

                # =================================
                # EXPLANATIONS
                # =================================

                for explanation in section.explanations:

                    exp_no = (
                        explanation.explanation_no
                        if explanation.explanation_no
                        else "UNNUMBERED"
                    )

                    explanation_id = (
                        f"{section_id}"
                        f"-EXP-{exp_no}"
                    )

                    exp_path = (
                        f"{section_path}"
                        f" > Explanation({exp_no})"
                    )

                    chunks.append(

                        LegalChunk(

                            chunk_id=
                                explanation_id,

                            level=
                                "explanation",

                            document=
                                document_name.lower(),

                            chapter_no=
                                chapter.chapter_no,

                            chapter_title=
                                chapter_title,

                            section_no=
                                section.section_no,

                            clause_no=
                                None,

                            sub_clause_no=
                                None,

                            roman_no=
                                None,

                            title=
                                title,

                            text=
                                explanation.text,

                            enriched_text=
                                self.build_context(
                                    document=
                                        document_name,

                                    chapter_no=
                                        chapter.chapter_no,

                                    chapter_title=
                                        chapter_title,

                                    section_no=
                                        section.section_no,

                                    title=
                                        title
                                )
                                + "\n\n"
                                + explanation.text,

                            parent_id=
                                section_id,

                            root_section_id=
                                section_id,

                            path=
                                exp_path
                        )
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