from dataclasses import dataclass, field
from typing import List


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
class RomanClause:
    roman_no: str
    text: str


@dataclass
class SubClause:
    sub_clause_no: str
    text: str
    roman_clauses: List[RomanClause] = field(
        default_factory=list
    )


@dataclass
class Clause:
    clause_no: str
    text: str
    sub_clauses: List[SubClause] = field(
        default_factory=list
    )


@dataclass
class Provision:
    provision_no: str
    title: str
    text: str

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


@dataclass
class Division:
    division_no: str
    title: str
    provisions: List[Provision] = field(
        default_factory=list
    )



@dataclass
class LegalDocument:

    document_type: str

    divisions: list = field(
        default_factory=list
    )

@dataclass
class Section:
    section_no: str
    section_title: str
    text: str
    clauses: List[Clause] = field(default_factory=list)


@dataclass
class Chapter:
    chapter_no: str
    chapter_title: str
    sections: List[Section] = field(default_factory=list)