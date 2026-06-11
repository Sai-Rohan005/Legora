# parsers/bns_parser.py

from __future__ import annotations

import re

from parsers.base_parser import BaseLegalParser

from models.legal_models import (
    Chapter,
    Section,
    Clause,
    SubClause,
    RomanClause,
    LegalDocument
)


class BNSParser(BaseLegalParser):

    CHAPTER_RE = re.compile(
        r"CHAPTER\s+([IVXLC]+)\s*\n+([^\n]+)",
        re.IGNORECASE
    )

    SECTION_RE = re.compile(
        r"(?m)^(\d+[A-Z]?)\.\s+(.+)$"
    )

    # -------------------------------------------------
    # CHAPTERS
    # -------------------------------------------------

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
                    "chapter_no":
                        match.group(1).strip(),

                    "chapter_title":
                        match.group(2).strip(),

                    "text":
                        text[start:end]
                }
            )

        return chapters

    # -------------------------------------------------
    # SECTIONS
    # -------------------------------------------------

    def extract_sections(self, chapter_text):

        matches = list(
            self.SECTION_RE.finditer(
                chapter_text
            )
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
                    "section_no":
                        match.group(1),

                    "section_title":
                        match.group(2).strip(),

                    "text":
                        chapter_text[
                            start:end
                        ].strip()
                }
            )

        return sections

    # -------------------------------------------------
    # MAIN PARSER
    # -------------------------------------------------

    def parse(self, raw_text):

        raw_text = self.clean(raw_text)

        parsed_chapters = []

        chapter_blocks = (
            self.extract_chapters(
                raw_text
            )
        )

        for chapter_data in chapter_blocks:

            chapter = Chapter(
                document="bns",
                chapter_no=
                    chapter_data[
                        "chapter_no"
                    ],

                chapter_title=
                    chapter_data[
                        "chapter_title"
                    ]
            )

            section_blocks = (
                self.extract_sections(
                    chapter_data["text"]
                )
            )

            for section_data in section_blocks:

                section = Section(
                    document="bns",

                    section_no=
                        section_data[
                            "section_no"
                        ],

                    section_title=
                        section_data[
                            "section_title"
                        ],

                    text=
                        section_data[
                            "text"
                        ]
                )

                # -------------------------
                # SUBSECTIONS (1),(2),(3)
                # -------------------------

                clause_blocks = (
                    self.extract_clauses(
                        section.text
                    )
                )

                for clause_data in clause_blocks:

                    clause = Clause(
                        document="bns",
                        clause_no=
                            clause_data[
                                "clause_no"
                            ],

                        text=
                            clause_data[
                                "text"
                            ]
                    )

                    # ---------------------
                    # (a)(b)(c)
                    # ---------------------

                    sub_blocks = (
                        self.extract_subclauses(
                            clause.text
                        )
                    )

                    for sub_data in sub_blocks:

                        sub_clause = (
                            SubClause(
                                sub_clause_no=
                                    sub_data[
                                        "sub_clause_no"
                                    ],

                                text=
                                    sub_data[
                                        "text"
                                    ]
                            )
                        )

                        # -----------------
                        # (i)(ii)(iii)
                        # -----------------

                        roman_blocks = (
                            self.extract_roman_clauses(
                                sub_clause.text
                            )
                        )

                        for roman_data in roman_blocks:

                            sub_clause.roman_clauses.append(
                                RomanClause(
                                    document="bns",
                                    roman_no=
                                        roman_data[
                                            "roman_no"
                                        ],

                                    text=
                                        roman_data[
                                            "text"
                                        ]
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

            parsed_chapters.append(
                chapter
            )

        return LegalDocument(
            document="bns",
            document_type="bns",
            divisions=parsed_chapters
        )