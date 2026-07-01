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

        if getattr(bns, "parts", None):
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

            # PARENT → CHILD
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

            self.store.merge_relationship(
                chapter_id,
                section_id,
                "HAS_SECTION"
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

    # =====================================================
    # EXPLANATIONS
    # =====================================================

    def _build_explanations(self, section, section_id):
        for idx, explanation in enumerate(getattr(section, "explanations", []), start=1):

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

    # =====================================================
    # ILLUSTRATIONS
    # =====================================================

    def _build_illustrations(self, section, section_id):
        for idx, illustration in enumerate(getattr(section, "illustrations", []), start=1):

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