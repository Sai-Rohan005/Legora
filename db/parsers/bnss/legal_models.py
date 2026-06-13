from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# =====================================================
# REFERENCE
# =====================================================

@dataclass
class Reference:

    source_section: str

    target_section: str

    reference_type: str = "section"


# =====================================================
# ROMAN CLAUSE
# =====================================================

@dataclass
class RomanClause:

    document: str

    roman_no: str

    text: str


# =====================================================
# SUB CLAUSE
# =====================================================

@dataclass
class SubClause:

    document: str

    sub_clause_no: str

    text: str

    roman_clauses: List[
        RomanClause
    ] = field(
        default_factory=list
    )


# =====================================================
# CLAUSE
# =====================================================

@dataclass
class Clause:

    document: str

    clause_no: str

    text: str

    sub_clauses: List[
        SubClause
    ] = field(
        default_factory=list
    )
    roman_clauses: List[RomanClause] = field(
        default_factory=list
    )


# =====================================================
# EXPLANATION
# =====================================================

@dataclass
class Explanation:

    document: str

    explanation_no: str

    text: str


# =====================================================
# ILLUSTRATION
# =====================================================

@dataclass
class Illustration:

    document: str

    illustration_no: str

    text: str


# =====================================================
# SECTION
# =====================================================

@dataclass
class Section:

    document: str

    section_no: str

    section_title: str

    text: str

    clauses: List[
        Clause
    ] = field(
        default_factory=list
    )

    explanations: List[
        Explanation
    ] = field(
        default_factory=list
    )

    illustrations: List[
        Illustration
    ] = field(
        default_factory=list
    )

    references: List[
        dict
    ] = field(
        default_factory=list
    )


# =====================================================
# CHAPTER
# =====================================================

@dataclass
class Chapter:

    document: str

    chapter_no: str

    chapter_title: str

    text: str

    sections: List[
        Section
    ] = field(
        default_factory=list
    )


# =====================================================
# MAIN DOCUMENT
# =====================================================

@dataclass
class BNSSDocument:

    document_name: str = (
        "Bharatiya Nyaya Sanhita, 2023"
    )

    chapters: List[
        Chapter
    ] = field(
        default_factory=list
    )