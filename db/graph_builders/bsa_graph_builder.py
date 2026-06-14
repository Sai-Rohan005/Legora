from __future__ import annotations

from db.neo4j_store import Neo4jStore


class BSAGraphBuilder:

    DOCUMENT_ID = "BSA"

    def __init__(
        self,
        store: Neo4jStore
    ):
        self.store = store

    # =====================================================
    # NODE FACTORY
    # =====================================================

    def _props(
        self,
        node_id: str,
        node_type: str,
        **kwargs
    ):

        return {
            "id": node_id,
            "document": "BSA",
            "node_type": node_type,
            **kwargs
        }

    # =====================================================
    # BUILD
    # =====================================================

    def build(
        self,
        bsa
    ):

        self._create_document()

        if getattr(
            bsa,
            "parts",
            []
        ):

            self._build_parts(
                bsa
            )

        else:

            self._build_chapters(
                bsa.chapters,
                self.DOCUMENT_ID
            )

    # =====================================================
    # DOCUMENT
    # =====================================================

    def _create_document(
        self
    ):

        self.store.merge_node(
            label="Document",
            node_id=self.DOCUMENT_ID,
            properties=self._props(
                self.DOCUMENT_ID,
                "Document",
                name="Bharatiya Sakshya Adhiniyam, 2023"
            )
        )

    # =====================================================
    # PARTS
    # =====================================================

    def _build_parts(
        self,
        bsa
    ):

        for part in bsa.parts:

            part_id = (
                f"BSA-PART-{part.part_no}"
            )

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

            self.store.merge_relationship(
                self.DOCUMENT_ID,
                part_id,
                "HAS_PART"
            )

            self._build_chapters(
                part.chapters,
                part_id
            )

    # =====================================================
    # CHAPTERS
    # =====================================================

    def _build_chapters(
        self,
        chapters,
        parent_id
    ):

        for chapter in chapters:

            chapter_id = (
                f"BSA-CH-{chapter.chapter_no}"
            )

            self.store.merge_node(
                label="Chapter",
                node_id=chapter_id,
                properties=self._props(
                    chapter_id,
                    "Chapter",
                    chapter_no=chapter.chapter_no,
                    title=chapter.title,
                    text=chapter.text
                )
            )

            self.store.merge_relationship(
                parent_id,
                chapter_id,
                "HAS_CHAPTER"
            )

            self._build_sections(
                chapter.sections,
                chapter_id
            )

    # =====================================================
    # SECTIONS
    # =====================================================

    def _build_sections(
        self,
        sections,
        chapter_id
    ):

        for section in sections:

            section_id = (
                f"BSA-{section.section_no}"
            )

            self.store.merge_node(
                label="Section",
                node_id=section_id,
                properties=self._props(
                    section_id,
                    "Section",
                    section_no=section.section_no,
                    title=section.title,
                    text=section.text
                )
            )

            self.store.merge_relationship(
                section_id,
                chapter_id,
                "BELONGS_TO"
            )

            self._build_clauses(
                section,
                section_id
            )

            self._build_explanations(
                section,
                section_id
            )

            self._build_illustrations(
                section,
                section_id
            )

            self._build_references(
                section,
                section_id
            )

    # =====================================================
    # CLAUSES
    # =====================================================

    def _build_clauses(
        self,
        section,
        section_id
    ):

        for clause in getattr(
            section,
            "clauses",
            []
        ):

            clause_id = (
                f"{section_id}"
                f"({clause.clause_no})"
            )

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
                clause_id,
                section_id,
                "BELONGS_TO"
            )

            for sub in getattr(
                clause,
                "sub_clauses",
                []
            ):

                sub_id = (
                    f"{clause_id}"
                    f"({sub.sub_clause_no})"
                )

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
                    sub_id,
                    clause_id,
                    "BELONGS_TO"
                )

                for roman in getattr(
                    sub,
                    "roman_clauses",
                    []
                ):

                    roman_id = (
                        f"{sub_id}"
                        f"({roman.roman_no})"
                    )

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
                        roman_id,
                        sub_id,
                        "BELONGS_TO"
                    )

    # =====================================================
    # EXPLANATIONS
    # =====================================================

    def _build_explanations(
        self,
        section,
        section_id
    ):

        for idx, explanation in enumerate(
            getattr(
                section,
                "explanations",
                []
            ),
            start=1
        ):

            explanation_id = (
                f"{section_id}-EXPL-{idx}"
            )

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
                explanation_id,
                section_id,
                "BELONGS_TO"
            )

    # =====================================================
    # ILLUSTRATIONS
    # =====================================================

    def _build_illustrations(
        self,
        section,
        section_id
    ):

        for idx, illustration in enumerate(
            getattr(
                section,
                "illustrations",
                []
            ),
            start=1
        ):

            illustration_id = (
                f"{section_id}-ILL-{idx}"
            )

            self.store.merge_node(
                label="Illustration",
                node_id=illustration_id,
                properties=self._props(
                    illustration_id,
                    "Illustration",
                    illustration_no=getattr(
                        illustration,
                        "illustration_no",
                        None
                    ),
                    text=illustration.text
                )
            )

            self.store.merge_relationship(
                illustration_id,
                section_id,
                "BELONGS_TO"
            )

    # =====================================================
    # REFERENCES
    # =====================================================

    def _build_references(
        self,
        section,
        section_id
    ):

        for ref in getattr(
            section,
            "references",
            []
        ):

            target = getattr(
                ref,
                "section_no",
                None
            )

            if not target:
                continue

            target_id = (
                f"BSA-{target}"
            )

            self.store.merge_relationship(
                section_id,
                target_id,
                "REFERENCES"
            )