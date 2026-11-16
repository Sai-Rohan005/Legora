
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ==========================================================
# BASE NODE
# ==========================================================

@dataclass
class LegalNode:
    """
    Base node used by all legal entities.
    """

    document: str

    id: Optional[str] = None

    parent_id: Optional[str] = None

    source_text: Optional[str] = None

    start_offset: Optional[int] = None

    end_offset: Optional[int] = None


# ==========================================================
# REFERENCES
# ==========================================================

@dataclass
class Reference:

    reference_type: str

    reference_value: str

    text: str = ""


# ==========================================================
# PROVISO
# ==========================================================

@dataclass
class Proviso(LegalNode):

    text: str = ""


# ==========================================================
# EXPLANATION
# ==========================================================

@dataclass
class Explanation(LegalNode):

    explanation_no: str = ""

    text: str = ""


# ==========================================================
# ILLUSTRATION
# ==========================================================

@dataclass
class Illustration(LegalNode):

    illustration_no: str = ""

    text: str = ""


# ==========================================================
# ROMAN CLAUSE
# ==========================================================

@dataclass
class RomanClause(LegalNode):

    roman_no: str = ""

    text: str = ""


# ==========================================================
# SUB CLAUSE
# ==========================================================

@dataclass
class SubClause(LegalNode):

    sub_clause_no: str = ""

    text: str = ""

    roman_clauses: List[RomanClause] = field(
        default_factory=list
    )


# ==========================================================
# CLAUSE
# ==========================================================

@dataclass
class Clause(LegalNode):

    clause_no: str = ""

    text: str = ""

    sub_clauses: List[SubClause] = field(
        default_factory=list
    )


# ==========================================================
# ARTICLE
# ==========================================================

@dataclass
class Article(LegalNode):

    article_no: str = ""

    article_title: str = ""

    text: str = ""

    clauses: List[Clause] = field(
        default_factory=list
    )

    provisos: List[Proviso] = field(
        default_factory=list
    )

    explanations: List[Explanation] = field(
        default_factory=list
    )

    illustrations: List[Illustration] = field(
        default_factory=list
    )

    references: List[Reference] = field(
        default_factory=list
    )


# ==========================================================
# CHAPTER
# ==========================================================

@dataclass
class Chapter(LegalNode):

    chapter_no: str = ""

    chapter_title: str = ""

    articles: List[Article] = field(
        default_factory=list
    )


# ==========================================================
# PART
# ==========================================================

@dataclass
class Part(LegalNode):

    part_no: str = ""

    part_title: str = ""

    chapters: List[Chapter] = field(
        default_factory=list
    )

    articles: List[Article] = field(
        default_factory=list
    )


# ==========================================================
# SCHEDULE PARAGRAPH
# ==========================================================

@dataclass
class ScheduleParagraph(LegalNode):

    paragraph_no: str = ""

    text: str = ""


# ==========================================================
# SCHEDULE
# ==========================================================

@dataclass
class Schedule(LegalNode):

    schedule_no: str = ""

    schedule_title: str = ""

    text: str = ""

    paragraphs: List[ScheduleParagraph] = field(
        default_factory=list
    )

    references: List[Reference] = field(
        default_factory=list
    )


# ==========================================================
# PREAMBLE
# ==========================================================

@dataclass
class Preamble(LegalNode):

    text: str = ""


# ==========================================================
# CONSTITUTION DOCUMENT
# ==========================================================

@dataclass
class ConstitutionDocument(LegalNode):

    title: str = "Constitution of India"

    preamble: Optional[Preamble] = None

    parts: List[Part] = field(
        default_factory=list
    )

    schedules: List[Schedule] = field(
        default_factory=list
    )


# ==========================================================
# UTILITIES
# ==========================================================

def build_id(
    prefix: str,
    value: str
) -> str:

    value = value.replace(" ", "_")

    return f"{prefix}:{value}"


def assign_ids(
    constitution: ConstitutionDocument
):

    constitution.id = "constitution"

    for part in constitution.parts:

        part.id = build_id(
            "part",
            part.part_no
        )

        part.parent_id = constitution.id

        for chapter in part.chapters:

            chapter.id = build_id(
                "chapter",
                chapter.chapter_no
            )

            chapter.parent_id = part.id

            for article in chapter.articles:

                article.id = build_id(
                    "article",
                    article.article_no
                )

                article.parent_id = chapter.id

        for article in part.articles:

            article.id = build_id(
                "article",
                article.article_no
            )

            article.parent_id = part.id

    for schedule in constitution.schedules:

        schedule.id = build_id(
            "schedule",
            schedule.schedule_no
        )

        schedule.parent_id = constitution.id
