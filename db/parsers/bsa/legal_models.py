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

    reference_text: str


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

    roman_clauses: List[RomanClause] = (
        field(default_factory=list)
    )


# =====================================================
# CLAUSE
# =====================================================

@dataclass
class Clause:

    document: str

    clause_no: str

    text: str

    sub_clauses: List[SubClause] = (
        field(default_factory=list)
    )
    roman_clauses: List["RomanClause"] = field(
        default_factory=list
    )


# =====================================================
# EXPLANATION
# =====================================================

@dataclass
class Explanation:

    document: str

    explanation_no: Optional[str]

    text: str


# =====================================================
# ILLUSTRATION
# =====================================================

@dataclass
class Illustration:

    document: str

    illustration_no: Optional[str]

    text: str


# =====================================================
# PROVISO
# =====================================================

@dataclass
class Proviso:

    document: str

    text: str


# =====================================================
# SECTION
# =====================================================

@dataclass
class Section:

    document: str

    section_no: str

    title: str

    text: str

    clauses: List[Clause] = (
        field(default_factory=list)
    )

    explanations: List[Explanation] = (
        field(default_factory=list)
    )

    illustrations: List[Illustration] = (
        field(default_factory=list)
    )

    provisos: List[Proviso] = (
        field(default_factory=list)
    )

    references: List[Reference] = (
        field(default_factory=list)
    )


# =====================================================
# CHAPTER
# =====================================================

@dataclass
class Chapter:

    document: str

    chapter_no: str

    title: str

    text:str

    sections: List[Section] = (
        field(default_factory=list)
    )


# =====================================================
# PART
# =====================================================

@dataclass
class Part:

    document: str

    part_no: str

    title: str

    text:str

    chapters: List[Chapter] = (
        field(default_factory=list)
    )



# =====================================================
# DOCUMENT
# =====================================================

@dataclass
class LegalDocument:

    document: str

    title: str=""

    parts: List[Part] = (
        field(default_factory=list)
    )

    chapters: List[Chapter] = (
        field(default_factory=list)
    )

    sections: List[Section] = (
        field(default_factory=list)
    )