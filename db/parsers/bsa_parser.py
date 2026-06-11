from __future__ import annotations

import re

from parsers.base_parser import BaseLegalParser

from models.legal_models import (
    LegalDocument,
    Division,
    Provision,
    Clause,
    SubClause,
    RomanClause
)


class BSAParser(BaseLegalParser):

    # =====================================================
    # REGEX
    # =====================================================

    PART_RE = re.compile(
        r"(?m)^PART\s+([IVXLC]+)"
    )

    CHAPTER_RE = re.compile(
        r"(?m)^CHAPTER\s+([IVXLC]+)\s*\n+([^\n]+)"
    )

    SECTION_RE = re.compile(
        r"(?m)^(\d+[A-Z]?)\.\s*(.+)"
    )

    CLAUSE_RE = re.compile(
        r"(?m)^\((\d+)\)\s*(.*)"
    )

    SUBCLAUSE_RE = re.compile(
        r"(?m)^\(([a-z])\)\s*(.*)"
    )

    ROMAN_RE = re.compile(
        r"(?m)^\((i|ii|iii|iv|v|vi|vii|viii|ix|x)\)\s*(.*)",
        re.IGNORECASE
    )

    # =====================================================
    # CLEAN
    # =====================================================

    def clean(self, text):

        text = super().clean(text)

        text = re.sub(
            r"THE GAZETTE OF INDIA EXTRAORDINARY.*",
            "",
            text
        )

        text = re.sub(
            r"_{5,}",
            "",
            text
        )

        return text

    # =====================================================
    # PARTS
    # =====================================================

    def extract_parts(self, text):

        matches = list(
            self.PART_RE.finditer(text)
        )

        results = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append(
                {
                    "part_no":
                        match.group(1),

                    "text":
                        text[start:end]
                }
            )

        return results

    # =====================================================
    # CHAPTERS
    # =====================================================

    def extract_chapters(self, text):

        matches = list(
            self.CHAPTER_RE.finditer(text)
        )

        results = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append(
                {
                    "chapter_no":
                        match.group(1),

                    "chapter_title":
                        match.group(2).strip(),

                    "text":
                        text[start:end]
                }
            )

        return results

    # =====================================================
    # SECTIONS
    # =====================================================

    def extract_sections(self, text):

        matches = list(
            self.SECTION_RE.finditer(text)
        )

        results = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            section_no = match.group(1)

            title = match.group(2).strip()

            results.append(
                {
                    "section_no":
                        section_no,

                    "section_title":
                        title,

                    "text":
                        text[start:end]
                }
            )

        return results

    # =====================================================
    # CLAUSES
    # =====================================================

    def extract_clauses(self, text):

        matches = list(
            self.CLAUSE_RE.finditer(text)
        )

        results = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append(
                {
                    "clause_no":
                        match.group(1),

                    "text":
                        text[start:end].strip()
                }
            )

        return results

    # =====================================================
    # SUB CLAUSES
    # =====================================================

    def extract_subclauses(self, text):

        matches = list(
            self.SUBCLAUSE_RE.finditer(text)
        )

        results = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append(
                {
                    "sub_clause_no":
                        match.group(1),

                    "text":
                        text[start:end].strip()
                }
            )

        return results

    # =====================================================
    # ROMAN CLAUSES
    # =====================================================

    def extract_roman_clauses(self, text):

        matches = list(
            self.ROMAN_RE.finditer(text)
        )

        results = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append(
                {
                    "roman_no":
                        match.group(1),

                    "text":
                        text[start:end].strip()
                }
            )

        return results

    # =====================================================
    # MAIN PARSER
    # =====================================================

    def parse(self, raw_text):

        raw_text = self.clean(raw_text)

        divisions = []

        for part_data in self.extract_parts(raw_text):

            part_no = part_data["part_no"]

            for chapter_data in self.extract_chapters(
                part_data["text"]
            ):

                division = Division(
                    document="bsa",
                    division_no=chapter_data["chapter_no"],
                    title=chapter_data["chapter_title"]
                )

                for section_data in self.extract_sections(
                    chapter_data["text"]
                ):

                    provision = Provision(
                        document="bsa",
                        provision_no=section_data["section_no"],
                        title=section_data["section_title"],
                        text=section_data["text"]
                    )

                    # ---------------------
                    # Clauses
                    # ---------------------

                    for clause_data in self.extract_clauses(
                        provision.text
                    ):

                        clause = Clause(
                            document="bsa",
                            clause_no=clause_data["clause_no"],
                            text=clause_data["text"]
                        )

                        # -----------------
                        # Sub Clauses
                        # -----------------

                        for sub_data in self.extract_subclauses(
                            clause.text
                        ):

                            sub = SubClause(
                                document="bsa",
                                sub_clause_no=sub_data["sub_clause_no"],
                                text=sub_data["text"]
                            )

                            # -------------
                            # Roman
                            # -------------

                            for roman_data in self.extract_roman_clauses(
                                sub.text
                            ):

                                sub.roman_clauses.append(
                                    RomanClause(
                                        document="bsa",
                                        roman_no=roman_data["roman_no"],
                                        text=roman_data["text"]
                                    )
                                )

                            clause.sub_clauses.append(sub)

                        provision.clauses.append(clause)

                    provision.references = (
                        self.extract_references(
                            provision.text
                        )
                    )

                    division.provisions.append(
                        provision
                    )

                division.part_no = part_no

                divisions.append(
                    division
                )

        return LegalDocument(
            document="bsa",
            document_type="bsa",
            divisions=divisions
        )