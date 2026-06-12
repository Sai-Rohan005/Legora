
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any
from parsers.consitution.constitution_parser import ConstitutionParser

# =========================================================
# LEGAL CHUNK
# =========================================================

@dataclass
class LegalChunk:

    chunk_id: str

    chunk_type: str

    text: str

    metadata: Dict[str, Any] = field(
        default_factory=dict
    )

    references: List[str] = field(
        default_factory=list
    )


# =========================================================
# LEGAL CHUNKER
# =========================================================

class LegalChunker:

    """
    Creates chunks at:

        Article
        Clause
        Proviso
        Explanation
        Schedule

    for RAG retrieval.
    """

    # =====================================================
    # MAIN
    # =====================================================

    def chunk_constitution(
        self,
        constitution
    ) -> List[LegalChunk]:

        chunks = []

        # -------------------------------------
        # PARTS
        # -------------------------------------

        for part in constitution.parts:

            part_meta = {
                "part_no":
                    part.part_no,

                "part_title":
                    part.part_title
            }

            # -------------------------
            # Articles directly under part
            # -------------------------

            for article in getattr(
                part,
                "articles",
                []
            ):

                chunks.extend(
                    self.chunk_article(
                        article,
                        part_meta,
                        {}
                    )
                )

            # -------------------------
            # Chapters
            # -------------------------

            for chapter in getattr(
                part,
                "chapters",
                []
            ):

                chapter_meta = {
                    "chapter_no":
                        chapter.chapter_no,

                    "chapter_title":
                        chapter.chapter_title
                }

                for article in getattr(
                    chapter,
                    "articles",
                    []
                ):

                    chunks.extend(
                        self.chunk_article(
                            article,
                            part_meta,
                            chapter_meta
                        )
                    )

        # -------------------------------------
        # SCHEDULES
        # -------------------------------------

        for schedule in getattr(
            constitution,
            "schedules",
            []
        ):

            chunks.append(
                LegalChunk(
                    chunk_id=
                        f"schedule_"
                        f"{schedule.schedule_no}",

                    chunk_type=
                        "schedule",

                    text=
                        schedule.text,

                    metadata={
                        "schedule_no":
                            schedule.schedule_no,

                        "schedule_title":
                            schedule.schedule_title
                    }
                )
            )

        return chunks

    # =====================================================
    # ARTICLE
    # =====================================================

    def chunk_article(
        self,
        article,
        part_meta,
        chapter_meta
    ) -> List[LegalChunk]:

        chunks = []

        base_meta = {
            **part_meta,
            **chapter_meta,

            "article_no":
                article.article_no,

            "article_title":
                article.article_title
        }

        # -------------------------------------
        # FULL ARTICLE
        # -------------------------------------

        chunks.append(
            LegalChunk(
                chunk_id=
                    f"article_"
                    f"{article.article_no}",

                chunk_type=
                    "article",

                text=
                    article.text,

                metadata=
                    base_meta,

                references=[
                    str(r)
                    for r in getattr(
                        article,
                        "references",
                        []
                    )
                ]
            )
        )

        # -------------------------------------
        # CLAUSES
        # -------------------------------------

        for clause in getattr(
            article,
            "clauses",
            []
        ):

            clause_meta = {
                **base_meta,

                "clause_no":
                    clause.clause_no
            }

            chunks.append(
                LegalChunk(
                    chunk_id=
                        f"article_"
                        f"{article.article_no}"
                        f"_clause_"
                        f"{clause.clause_no}",

                    chunk_type=
                        "clause",

                    text=
                        clause.text,

                    metadata=
                        clause_meta
                )
            )

            # -----------------------------
            # SUB CLAUSES
            # -----------------------------

            for sub in getattr(
                clause,
                "sub_clauses",
                []
            ):

                sub_meta = {
                    **clause_meta,

                    "sub_clause_no":
                        sub.sub_clause_no
                }

                chunks.append(
                    LegalChunk(
                        chunk_id=
                            f"article_"
                            f"{article.article_no}"
                            f"_clause_"
                            f"{clause.clause_no}"
                            f"_sub_"
                            f"{sub.sub_clause_no}",

                        chunk_type=
                            "sub_clause",

                        text=
                            sub.text,

                        metadata=
                            sub_meta
                    )
                )

                # -------------------------
                # Roman Clauses
                # -------------------------

                for roman in getattr(
                    sub,
                    "roman_clauses",
                    []
                ):

                    chunks.append(
                        LegalChunk(
                            chunk_id=
                                f"article_"
                                f"{article.article_no}"
                                f"_roman_"
                                f"{roman.roman_no}",

                            chunk_type=
                                "roman_clause",

                            text=
                                roman.text,

                            metadata={
                                **sub_meta,

                                "roman_no":
                                    roman.roman_no
                            }
                        )
                    )

        # -------------------------------------
        # PROVISOS
        # -------------------------------------

        for idx, proviso in enumerate(
            getattr(
                article,
                "provisos",
                []
            ),
            start=1
        ):

            chunks.append(
                LegalChunk(
                    chunk_id=
                        f"article_"
                        f"{article.article_no}"
                        f"_proviso_"
                        f"{idx}",

                    chunk_type=
                        "proviso",

                    text=
                        proviso.text,

                    metadata=
                        base_meta
                )
            )

        # -------------------------------------
        # EXPLANATIONS
        # -------------------------------------

        for idx, explanation in enumerate(
            getattr(
                article,
                "explanations",
                []
            ),
            start=1
        ):

            chunks.append(
                LegalChunk(
                    chunk_id=
                        f"article_"
                        f"{article.article_no}"
                        f"_explanation_"
                        f"{idx}",

                    chunk_type=
                        "explanation",

                    text=
                        explanation.text,

                    metadata=
                        base_meta
                )
            )

        return chunks

    # =====================================================
    # STATS
    # =====================================================

    def stats(
        self,
        chunks: List[LegalChunk]
    ):

        result = {}

        for chunk in chunks:

            result.setdefault(
                chunk.chunk_type,
                0
            )

            result[
                chunk.chunk_type
            ] += 1

        return result



if __name__ == "__main__":

    with open(
        "../../pdfs/constitution.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()

    parser = ConstitutionParser()

    constitution = parser.parse(
        text
    )
    chunker=LegalChunker()
    chunks=chunker.chunk_constitution(constitution)
    print(len(chunks))
    print(
        chunker.stats(chunks)
    )

    