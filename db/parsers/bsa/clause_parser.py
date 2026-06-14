from __future__ import annotations

import re
from typing import List

from db.parsers.bsa.legal_models import (
    Clause,
    SubClause,
    RomanClause
)


class ClauseParser:

    # =====================================================
    # REGEX
    # =====================================================

    CLAUSE_RE = re.compile(
        r"(?m)^\s*\((\d+[A-Za-z]?)\)"
    )

    SUBCLAUSE_RE = re.compile(
        r"(?m)^\s*\(([a-z])\)"
    )

    ROMAN_RE = re.compile(
        r"(?m)^\s*\(([ivxlcdm]+)\)"
    )

    ROMAN_VALUES = {
        "i", "ii", "iii", "iv", "v",
        "vi", "vii", "viii", "ix", "x",
        "xi", "xii", "xiii", "xiv", "xv",
        "xvi", "xvii", "xviii", "xix", "xx"
    }

    STOP_WORDS = [
        "Explanation.",
        "Explanation.—",
        "Explanation.-",
        "Illustration.",
        "Illustrations.",
        "Exception.",
        "Exception.—",
        "Provided that",
        "Provided further that"
    ]

    # =====================================================
    # SPLITTER
    # =====================================================

    def split_sections(
        self,
        text: str,
        pattern: re.Pattern
    ):

        matches = list(
            pattern.finditer(text)
        )

        if not matches:
            return []

        sections = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            sections.append(
                (
                    match.group(1),
                    text[start:end].strip()
                )
            )

        return sections

    # =====================================================
    # CLEAN CLAUSE TEXT
    # =====================================================

    def clean_clause_text(
        self,
        text: str
    ) -> str:

        cutoff = len(text)

        for word in self.STOP_WORDS:

            pos = text.find(word)

            if pos != -1:

                cutoff = min(
                    cutoff,
                    pos
                )

        return text[:cutoff]

    # =====================================================
    # ROMAN CLAUSES
    # =====================================================

    def parse_roman_clauses(
        self,
        text: str
    ) -> List[RomanClause]:

        romans = []

        roman_sections = self.split_sections(
            text,
            re.compile(
                r"(?m)^\s*\((i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv|xvi|xvii|xviii|xix|xx)\)"
            )
        )

        for roman_no, roman_text in roman_sections:

            romans.append(
                RomanClause(
                    document="bsa",
                    roman_no=roman_no,
                    text=roman_text
                )
            )

        return romans

    # =====================================================
    # SUBCLAUSES
    # =====================================================

    def parse_subclauses(
        self,
        text: str
    ) -> List[SubClause]:

        subclauses = []

        sub_sections = self.split_sections(
            text,
            self.SUBCLAUSE_RE
        )

        for sub_no, sub_text in sub_sections:

            if (
                sub_no.lower()
                in self.ROMAN_VALUES
            ):
                continue

            sub = SubClause(
                document="bsa",
                sub_clause_no=sub_no,
                text=sub_text
            )

            sub.roman_clauses.extend(
                self.parse_roman_clauses(
                    sub_text
                )
            )

            subclauses.append(
                sub
            )

        return subclauses

    # =====================================================
    # CLAUSES
    # =====================================================

    def parse_clauses(
        self,
        section_text: str
    ) -> List[Clause]:

        section_text = re.sub(
            r"([;:—])\(([a-z])\)",
            r"\1\n(\2)",
            section_text
        )

        section_text = re.sub(
            r"([.;:—])\((\d+[A-Za-z]?)\)",
            r"\1\n(\2)",
            section_text
        )

        section_text = re.sub(
            r"(\d+\.)\s*(\(\d+[A-Za-z]?\))",
            r"\1\n\2",
            section_text
        )

        clauses = []

        # =================================================
        # NUMERIC CLAUSES
        # =================================================

        clause_sections = self.split_sections(
            section_text,
            self.CLAUSE_RE
        )

        if clause_sections:

            for clause_no, clause_text in clause_sections:

                clause = Clause(
                    document="bsa",
                    clause_no=clause_no,
                    text=clause_text
                )

                clean_text = self.clean_clause_text(
                    clause_text
                )

                clause.sub_clauses.extend(
                    self.parse_subclauses(
                        clean_text
                    )
                )

                if not clause.sub_clauses:

                    clause.roman_clauses.extend(
                        self.parse_roman_clauses(
                            clean_text
                        )
                    )

                clauses.append(
                    clause
                )

            return clauses

        # =================================================
        # BSA STYLE
        #
        # (a)
        # (b)
        # (c)
        #
        # WITHOUT (1)
        # =================================================

        alpha_sections = self.split_sections(
            section_text,
            self.SUBCLAUSE_RE
        )

        if alpha_sections:

            synthetic_clause = Clause(
                document="bsa",
                clause_no="0",
                text=section_text
            )

            for alpha_no, alpha_text in alpha_sections:

                if (
                    alpha_no.lower()
                    in self.ROMAN_VALUES
                ):
                    continue

                sub = SubClause(
                    document="bsa",
                    sub_clause_no=alpha_no,
                    text=alpha_text
                )

                sub.roman_clauses.extend(
                    self.parse_roman_clauses(
                        alpha_text
                    )
                )

                synthetic_clause.sub_clauses.append(
                    sub
                )

            clauses.append(
                synthetic_clause
            )

            return clauses

        return []

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_clauses(
        self,
        clauses: List[Clause]
    ) -> List[str]:

        errors = []

        clause_seen = set()

        for clause in clauses:

            if (
                clause.clause_no
                in clause_seen
            ):

                errors.append(
                    f"Duplicate Clause "
                    f"{clause.clause_no}"
                )

            clause_seen.add(
                clause.clause_no
            )

            # ---------------------------------
            # Romans directly under clause
            # ---------------------------------

            roman_seen = set()

            for roman in clause.roman_clauses:

                if (
                    roman.roman_no
                    in roman_seen
                ):

                    errors.append(
                        f"Duplicate Roman "
                        f"{roman.roman_no}"
                    )

                roman_seen.add(
                    roman.roman_no
                )

            # ---------------------------------
            # Subclauses
            # ---------------------------------

            sub_seen = set()

            for sub in clause.sub_clauses:

                if (
                    sub.sub_clause_no
                    in sub_seen
                ):

                    errors.append(
                        f"Duplicate SubClause "
                        f"{sub.sub_clause_no}"
                    )

                sub_seen.add(
                    sub.sub_clause_no
                )

                roman_seen = set()

                for roman in sub.roman_clauses:

                    if (
                        roman.roman_no
                        in roman_seen
                    ):

                        errors.append(
                            f"Duplicate Roman "
                            f"{roman.roman_no}"
                        )

                    roman_seen.add(
                        roman.roman_no
                    )

        return errors