from __future__ import annotations

from dataclasses import (
    dataclass,
    asdict
)

from typing import (
    List,
    Optional
)


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

    illustration_no: Optional[str]

    explanation_no: Optional[str]

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
        document_name="BSA"
    ):
        self.document_name = document_name

    # =====================================================
    # CONTEXT
    # =====================================================

    def build_context(
        self,
        title="",
        section_no="",
        clause_no="",
        sub_clause_no="",
        roman_no="",
        illustration_no="",
        explanation_no=""
    ):

        parts = [
            self.document_name
        ]

        if section_no:
            parts.append(
                f"Section {section_no}"
            )

        if title:
            parts.append(title)

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
                f"Roman ({roman_no})"
            )

        if explanation_no:
            parts.append(
                f"Explanation {explanation_no}"
            )

        if illustration_no:
            parts.append(
                f"Illustration {illustration_no}"
            )

        return "\n".join(parts)

    # =====================================================
    # MAIN
    # =====================================================

    def chunk_document(
        self,
        document
    ) -> List[LegalChunk]:

        chunks = []

        for chapter in document.chapters:

            for section in chapter.sections:

                section_id = (
                    f"BSA-{section.section_no}"
                )

                title = getattr(
                    section,
                    "title",
                    getattr(
                        section,
                        "section_title",
                        ""
                    )
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
                            "bsa",

                        chapter_no=
                            chapter.chapter_no,

                        section_no=
                            section.section_no,

                        clause_no=None,
                        sub_clause_no=None,
                        roman_no=None,

                        illustration_no=None,
                        explanation_no=None,

                        title=
                            title,

                        text=
                            section.text,

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
                )

                # =================================
                # CLAUSES
                # =================================

                for clause in section.clauses:

                    clause_id = (
                        f"{section_id}"
                        f"({clause.clause_no})"
                    )

                    chunks.append(
                        LegalChunk(
                            chunk_id=
                                clause_id,

                            level=
                                "clause",

                            document=
                                "bsa",

                            chapter_no=
                                chapter.chapter_no,

                            section_no=
                                section.section_no,

                            clause_no=
                                clause.clause_no,

                            sub_clause_no=None,
                            roman_no=None,

                            illustration_no=None,
                            explanation_no=None,

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
                    )

                    # =============================
                    # SUBCLAUSES
                    # =============================

                    for sub in clause.sub_clauses:

                        sub_id = (
                            f"{clause_id}"
                            f"({sub.sub_clause_no})"
                        )

                        chunks.append(
                            LegalChunk(
                                chunk_id=
                                    sub_id,

                                level=
                                    "subclause",

                                document=
                                    "bsa",

                                chapter_no=
                                    chapter.chapter_no,

                                section_no=
                                    section.section_no,

                                clause_no=
                                    clause.clause_no,

                                sub_clause_no=
                                    sub.sub_clause_no,

                                roman_no=None,

                                illustration_no=None,
                                explanation_no=None,

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
                        )

                        # =========================
                        # ROMANS
                        # =========================

                        for roman in sub.roman_clauses:

                            roman_id = (
                                f"{sub_id}"
                                f"({roman.roman_no})"
                            )

                            chunks.append(
                                LegalChunk(
                                    chunk_id=
                                        roman_id,

                                    level=
                                        "roman",

                                    document=
                                        "bsa",

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

                                    illustration_no=None,
                                    explanation_no=None,

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
                            )

                # =================================
                # EXPLANATIONS
                # =================================

                for exp in section.explanations:

                    exp_no = (
                        exp.explanation_no
                        or "0"
                    )

                    exp_id = (
                        f"{section_id}"
                        f"-EXP-{exp_no}"
                    )

                    chunks.append(
                        LegalChunk(
                            chunk_id=
                                exp_id,

                            level=
                                "explanation",

                            document=
                                "bsa",

                            chapter_no=
                                chapter.chapter_no,

                            section_no=
                                section.section_no,

                            clause_no=None,
                            sub_clause_no=None,
                            roman_no=None,

                            illustration_no=None,

                            explanation_no=
                                exp_no,

                            title=
                                title,

                            text=
                                exp.text,

                            enriched_text=
                                self.build_context(
                                    title=title,
                                    section_no=
                                        section.section_no,
                                    explanation_no=
                                        exp_no
                                )
                                + "\n\n"
                                + exp.text,

                            parent_id=
                                section_id
                        )
                    )

                # =================================
                # ILLUSTRATIONS
                # =================================

                for ill in section.illustrations:

                    ill_no = (
                        ill.illustration_no
                        or "0"
                    )

                    ill_id = (
                        f"{section_id}"
                        f"-ILL-{ill_no}"
                    )

                    chunks.append(
                        LegalChunk(
                            chunk_id=
                                ill_id,

                            level=
                                "illustration",

                            document=
                                "bsa",

                            chapter_no=
                                chapter.chapter_no,

                            section_no=
                                section.section_no,

                            clause_no=None,
                            sub_clause_no=None,
                            roman_no=None,

                            illustration_no=
                                ill_no,

                            explanation_no=None,

                            title=
                                title,

                            text=
                                ill.text,

                            enriched_text=
                                self.build_context(
                                    title=title,
                                    section_no=
                                        section.section_no,
                                    illustration_no=
                                        ill_no
                                )
                                + "\n\n"
                                + ill.text,

                            parent_id=
                                section_id
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