from __future__ import annotations

from db.neo4j_store import Neo4jStore


class ConstitutionGraphBuilder:

    DOCUMENT_ID = "CONST"

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
            "document": "CONSTITUTION",
            "node_type": node_type,
            **kwargs
        }

    # =====================================================
    # BUILD
    # =====================================================

    def build(
        self,
        constitution
    ):

        self._create_document_node()

        self._build_parts(
            constitution
        )

        self._build_schedules(
            constitution
        )

    # =====================================================
    # DOCUMENT
    # =====================================================

    def _create_document_node(
        self
    ):

        self.store.merge_node(
            label="Document",
            node_id=self.DOCUMENT_ID,
            properties=self._props(
                self.DOCUMENT_ID,
                "Document",
                name="Constitution of India"
            )
        )

    # =====================================================
    # PARTS
    # =====================================================

    def _build_parts(
        self,
        constitution
    ):

        for part in constitution.parts:

            part_id = (
                f"CONST-PART-{part.part_no}"
            )

            self.store.merge_node(
                label="Part",
                node_id=part_id,
                properties=self._props(
                    part_id,
                    "Part",
                    part_no=part.part_no,
                    title=part.part_title,
                )
            )

        

            self.store.merge_relationship(
                part_id,
                self.DOCUMENT_ID,
                "BELONGS_TO"
            )

            # Articles directly under Part

            for article in getattr(
                part,
                "articles",
                []
            ):

                article_id = (
                    self._build_article(
                        article,
                        part_id
                    )
                )

                self.store.merge_relationship(
                    part_id,
                    article_id,
                    "HAS_ARTICLE"
                )

            # Chapters

            for chapter in getattr(
                part,
                "chapters",
                []
            ):

                chapter_id = (
                    self._build_chapter(
                        chapter,
                        part_id
                    )
                )

                self.store.merge_relationship(
                    part_id,
                    chapter_id,
                    "HAS_CHAPTER"
                )

    # =====================================================
    # CHAPTER
    # =====================================================

    def _build_chapter(
        self,
        chapter,
        parent_id
    ):

        chapter_id = (
            f"CONST-CH-{chapter.chapter_no}"
        )

        self.store.merge_node(
            label="Chapter",
            node_id=chapter_id,
            properties=self._props(
                chapter_id,
                "Chapter",
                chapter_no=chapter.chapter_no,
                title=chapter.chapter_title,
                # text=chapter.text
            )
        )

        self.store.merge_relationship(
            chapter_id,
            parent_id,
            "BELONGS_TO"
        )

        for article in getattr(
            chapter,
            "articles",
            []
        ):

            article_id = (
                self._build_article(
                    article,
                    chapter_id
                )
            )

            self.store.merge_relationship(
                chapter_id,
                article_id,
                "HAS_ARTICLE"
            )

        return chapter_id

    # =====================================================
    # ARTICLE
    # =====================================================

    def _build_article(
        self,
        article,
        parent_id
    ):

        article_id = (
            f"CONST-{article.article_no}"
        )

        self.store.merge_node(
            label="Article",
            node_id=article_id,
            properties=self._props(
                article_id,
                "Article",
                article_no=article.article_no,
                title=article.article_title,
                text=article.text
            )
        )

        self.store.merge_relationship(
            article_id,
            parent_id,
            "BELONGS_TO"
        )

        # Clauses

        for clause in getattr(
            article,
            "clauses",
            []
        ):

            clause_id = (
                self._build_clause(
                    clause,
                    article_id
                )
            )

            self.store.merge_relationship(
                article_id,
                clause_id,
                "HAS_CLAUSE"
            )

        # Provisos

        for idx, proviso in enumerate(
            getattr(
                article,
                "provisos",
                []
            ),
            start=1
        ):

            proviso_id = (
                f"{article_id}-PROVISO-{idx}"
            )

            self.store.merge_node(
                label="Proviso",
                node_id=proviso_id,
                properties=self._props(
                    proviso_id,
                    "Proviso",
                    text=proviso.text
                )
            )

            

            self.store.merge_relationship(
                proviso_id,
                article_id,
                "BELONGS_TO"
            )

        # Explanations

        for idx, explanation in enumerate(
            getattr(
                article,
                "explanations",
                []
            ),
            start=1
        ):

            explanation_id = (
                f"{article_id}-EXPL-{idx}"
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
                article_id,
                "BELONGS_TO"
            )

        self._build_references(
            article,
            article_id
        )

        return article_id

    # =====================================================
    # CLAUSE
    # =====================================================

    def _build_clause(
        self,
        clause,
        article_id
    ):

        clause_id = (
            f"{article_id}"
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
            article_id,
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

        return clause_id

    # =====================================================
    # REFERENCES
    # =====================================================

    def _build_references(
        self,
        article,
        article_id
    ):

        for ref in getattr(
            article,
            "references",
            []
        ):

            target_article = getattr(
                ref,
                "article_no",
                None
            )

            if not target_article:
                continue

            target_id = (
                f"CONST-{target_article}"
            )

            self.store.merge_relationship(
                article_id,
                target_id,
                "REFERENCES"
            )

    # =====================================================
    # SCHEDULES
    # =====================================================

    def _build_schedules(
        self,
        constitution
    ):

        for schedule in getattr(
            constitution,
            "schedules",
            []
        ):

            schedule_id = (
                f"CONST-SCH-{schedule.schedule_no}"
            )

            self.store.merge_node(
                label="Schedule",
                node_id=schedule_id,
                properties=self._props(
                    schedule_id,
                    "Schedule",
                    schedule_no=schedule.schedule_no,
                    title=schedule.schedule_title,
                    text=schedule.text
                )
            )

            

            self.store.merge_relationship(
                schedule_id,
                self.DOCUMENT_ID,
                "BELONGS_TO"
            )