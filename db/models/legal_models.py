from dataclasses import dataclass, field
from typing import List


# ==========================================
# BASE NODE (SAFE FOR INHERITANCE)
# ==========================================

@dataclass(kw_only=True)
class BaseNode:
    document: str = ""


# ==========================================
# LOWEST LEVEL ENTITIES
# ==========================================

@dataclass
class Reference:
    provision_no: str


@dataclass
class Explanation:
    text: str


@dataclass
class Illustration:
    text: str


@dataclass
class Proviso:
    text: str


@dataclass
class RomanClause(BaseNode):
    roman_no: str
    text: str


@dataclass
class SubClause(BaseNode):
    sub_clause_no: str
    text: str
    roman_clauses: List[RomanClause] = field(default_factory=list)


@dataclass
class Clause(BaseNode):
    clause_no: str
    text: str
    sub_clauses: List[SubClause] = field(default_factory=list)


# ==========================================
# PROVISION LEVEL
# ==========================================

@dataclass
class Provision(BaseNode):
    provision_no: str
    title: str
    text: str

    clauses: List[Clause] = field(default_factory=list)
    provisos: List[Proviso] = field(default_factory=list)
    explanations: List[Explanation] = field(default_factory=list)
    illustrations: List[Illustration] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)


# ==========================================
# DIVISION / CHAPTER LEVEL
# ==========================================

@dataclass
class Division(BaseNode):
    division_no: str
    title: str
    provisions: List[Provision] = field(default_factory=list)


# ==========================================
# ROOT DOCUMENT
# (does NOT inherit BaseNode intentionally)
# ==========================================

@dataclass
class LegalDocument(BaseNode   ):
    document_type: str
    divisions: List[Division] = field(default_factory=list)


# ==========================================
# BSA / BNSS STRUCTURE
# ==========================================

@dataclass
class Section(BaseNode):
    section_no: str
    section_title: str
    text: str
    clauses: List[Clause] = field(default_factory=list)


@dataclass
class Chapter(BaseNode):
    chapter_no: str
    chapter_title: str
    sections: List[Section] = field(default_factory=list)


@dataclass
class Article(BaseNode):
    article_no: str
    article_title: str
    text: str

    clauses: List[Clause] = field(default_factory=list)
    provisos: List[Proviso] = field(default_factory=list)
    explanations: List[Explanation] = field(default_factory=list)
    references: List[Reference] = field(default_factory=list)



@dataclass
class Part(BaseNode):
    part_no: str
    part_title: str
    articles: List[Article] = field(default_factory=list)
