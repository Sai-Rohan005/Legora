# parsers/bnss_parser.py

from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import List

from parsers.base_parser import (
    BaseLegalParser,
    
)
from models.legal_models import (
    BaseNode,
    Chapter,
    Section,
    Clause,
    SubClause,
    RomanClause,
)



# ---------------------------------------------------
# DATA MODELS
# ---------------------------------------------------

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


# ---------------------------------------------------
# PARSER
# ---------------------------------------------------

class BNSSParser(BaseLegalParser):

    CHAPTER_RE = re.compile(
        r"CHAPTER\s+([IVXLC]+)\s*\n+([^\n]+)",
        re.IGNORECASE
    )

    SECTION_RE = re.compile(
        r"(?m)^(\d{1,3}[A-Z]?)\.\s*(.+)$"
    )

    # -------------------------------------------
    # CHAPTER EXTRACTION
    # -------------------------------------------

    def extract_chapters(self, text):

        matches = list(
            self.CHAPTER_RE.finditer(text)
        )

        chapters = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            chapters.append(
                {
                    "chapter_no": match.group(1).strip(),
                    "chapter_title": match.group(2).strip(),
                    "text": text[start:end]
                }
            )

        return chapters

    # -------------------------------------------
    # SECTION EXTRACTION
    # -------------------------------------------

    def extract_sections(self, chapter_text):

        matches = list(
            self.SECTION_RE.finditer(chapter_text)
        )

        sections = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(chapter_text)
            )

            sections.append(
                {
                    "section_no": match.group(1).strip(),
                    "section_title": match.group(2).strip(),
                    "text": chapter_text[start:end].strip()
                }
            )

        return sections

    # -------------------------------------------
    # MAIN PARSE
    # -------------------------------------------

    def parse(self, raw_text):

        raw_text = self.clean(raw_text)

        chapters = []

        for chapter_data in self.extract_chapters(raw_text):

            chapter = Chapter(
                document="bnss",
                chapter_no=chapter_data["chapter_no"],
                chapter_title=chapter_data["chapter_title"]
            )

            for section_data in self.extract_sections(
                chapter_data["text"]
            ):

                section = Section(
                    document="bnss",
                    section_no=section_data["section_no"],
                    section_title=section_data["section_title"],
                    text=section_data["text"]
                )

                # -----------------------------
                # Clauses
                # -----------------------------

                clause_data = self.extract_chapters(
                    section.text
                )

                for c in clause_data:

                    clause = Clause(
                        clause_no=c["clause_no"],
                        text=c["text"]
                    )

                    # -------------------------
                    # Sub Clauses
                    # -------------------------

                    sub_clause_data = (
                        self.extract_subclauses(
                            clause.text
                        )
                    )

                    for s in sub_clause_data:

                        sub_clause = SubClause(
                            document="bnss",
                            sub_clause_no=s["sub_clause_no"],
                            text=s["text"]
                        )

                        # ---------------------
                        # Roman Clauses
                        # ---------------------

                        roman_data = (
                            self.extract_roman_clauses(
                                sub_clause.text
                            )
                        )

                        for r in roman_data:

                            sub_clause.roman_clauses.append(
                                RomanClause(
                                    document="bnss",
                                    roman_no=r["roman_no"],
                                    text=r["text"]
                                )
                            )

                        clause.sub_clauses.append(
                            sub_clause
                        )

                    section.clauses.append(
                        clause
                    )

                chapter.sections.append(
                    section
                )

            chapters.append(chapter)

        return chapters