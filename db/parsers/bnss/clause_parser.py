from __future__ import annotations

import re
from typing import List

from cleaner import BNSSTextCleaner
from legal_models import (
    Clause,
    SubClause,
    RomanClause
)


class ClauseParser:

    """
    BNS Clause Parser

    Supports:

        (1)
        (2)
        (2A)

    Sub Clauses:

        (a)
        (b)

    Roman Clauses:

        (i)
        (ii)
        (iii)

    """

    # =====================================================
    # REGEX
    # =====================================================
    
    CLAUSE_RE = re.compile(
        r"(?m)^(?:\s*)\((\d+[A-Za-z]?)\)"
    )

    SUBCLAUSE_RE = re.compile(
        r"(?m)^\s*\(([a-z])\)"
    )

    ROMAN_RE = re.compile(
        r"(?m)^\s*\(([ivxlcdm]+)\)"
    )

    # =====================================================
    # SPLIT SECTIONS
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
    # ROMAN CLAUSES
    # =====================================================

    def parse_roman_clauses(
        self,
        text: str
    ) -> List[RomanClause]:

        romans = []

        roman_sections = (
            self.split_sections(
                text,
                self.ROMAN_RE
            )
        )

        for roman_no, roman_text in roman_sections:

            romans.append(
                RomanClause(
                    document="bnss",
                    roman_no=roman_no,
                    text=roman_text
                )
            )

        return romans

    # =====================================================
    # SUB CLAUSES
    # =====================================================

    ROMAN_VALUES = {
    "i", "ii", "iii", "iv", "v",
    "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv",
    "xvi", "xvii", "xviii", "xix", "xx"
    }

    def parse_subclauses(
        self,
        text: str
    ) -> List[SubClause]:

        subclauses = []

        sub_sections = (
            self.split_sections(
                text,
                self.SUBCLAUSE_RE
            )
        )

        for sub_no, sub_text in sub_sections:

            # Skip roman numerals
            if (
                sub_no.lower()
                in self.ROMAN_VALUES
            ):
                continue

            sub = SubClause(
                document="bnss",
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

        # Normalize inline markers

        section_text = re.sub(
            r"([;:—])\(([a-z])\)",
            r"\1\n(\2)",
            section_text
        )

        section_text = re.sub(
            r"([.—])\((\d+[A-Za-z]?)\)",
            r"\1\n(\2)",
            section_text
        )

        clauses = []

        clause_sections = self.split_sections(
            section_text,
            self.CLAUSE_RE
        )

        def remove_non_clause_parts(
            text: str
        ) -> str:

            stop_words = [
                "Explanation.",
                "Explanation.—",
                "Explanation.––",
                "Illustration.",
                "Illustrations.",
                "Exception.",
                "Exception.—"
            ]

            cutoff = len(text)

            for word in stop_words:

                pos = text.find(word)

                if pos != -1:
                    cutoff = min(
                        cutoff,
                        pos
                    )

            return text[:cutoff]

        # ----------------------------------
        # No numbered clauses
        # ----------------------------------

        if not clause_sections:

            clean_text = remove_non_clause_parts(
                section_text
            )

            subclauses = self.parse_subclauses(
                clean_text
            )

            if subclauses:

                synthetic_clause = Clause(
                    document="bnss",
                    clause_no="0",
                    text=section_text
                )

                synthetic_clause.sub_clauses.extend(
                    subclauses
                )

                clauses.append(
                    synthetic_clause
                )

            return clauses

        # ----------------------------------
        # Numbered clauses
        # ----------------------------------

        for clause_no, original_clause_text in clause_sections:

            clause = Clause(
                document="bnss",
                clause_no=clause_no,
                text=original_clause_text
            )

            clean_clause_text = (
                remove_non_clause_parts(
                    original_clause_text
                )
            )

            clause.sub_clauses.extend(
                self.parse_subclauses(
                    clean_clause_text
                )
            )

            # Handle direct roman clauses
            if not clause.sub_clauses:

                clause.roman_clauses.extend(
                    self.parse_roman_clauses(
                        clean_clause_text
                    )
                )

            clauses.append(
                clause
            )

        return clauses


    def parse_section_structure(
        self,
        section_text: str
    ) -> List[Clause]:

        has_numeric = bool(
            self.NUMERIC_RE.search(
                section_text
            )
        )

        has_alpha = bool(
            self.ALPHA_RE.search(
                section_text
            )
        )

        has_capital = bool(
            self.CAPITAL_RE.search(
                section_text
            )
        )

        has_roman = bool(
            self.ROMAN_RE.search(
                section_text
            )
        )

        # =====================================
        # PLAIN SECTION
        # =====================================

        if (
            not has_numeric
            and not has_alpha
            and not has_capital
            and not has_roman
        ):
            return []

        # =====================================
        # ALPHA ONLY
        # (a)(b)(c)
        # =====================================

        if (
            not has_numeric
            and has_alpha
            and not has_capital
            and not has_roman
        ):
            return self.parse_alpha_clauses(
                section_text
            )

        # =====================================
        # NUMERIC ONLY
        # (1)(2)(3)
        # =====================================

        if (
            has_numeric
            and not has_alpha
            and not has_capital
            and not has_roman
        ):
            return self.parse_numeric_clauses(
                section_text
            )

        # =====================================
        # NUMERIC -> ALPHA
        # =====================================

        if (
            has_numeric
            and has_alpha
            and not has_capital
            and not has_roman
        ):
            return self.parse_numeric_alpha(
                section_text
            )

        # =====================================
        # NUMERIC -> ALPHA -> ROMAN
        # =====================================

        if (
            has_numeric
            and has_alpha
            and not has_capital
            and has_roman
        ):
            return self.parse_numeric_alpha_roman(
                section_text
            )

        # =====================================
        # ALPHA -> ROMAN
        # (a)
        #   (i)
        # =====================================

        if (
            not has_numeric
            and has_alpha
            and not has_capital
            and has_roman
        ):
            return self.parse_alpha_roman(
                section_text
            )

        # =====================================
        # CAPITAL -> ROMAN
        # (A)
        #   (i)
        # =====================================

        if (
            not has_numeric
            and has_alpha
            and has_capital
            and has_roman
        ):
            return self.parse_capital_roman(
                section_text
            )

        return []








    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_clauses(
        self,
        section_no,
        clauses: List[Clause]
    ) -> List[str]:

        errors = []

        seen = set()

        for clause in clauses:

            # if clause.clause_no in seen:

            #     print(
            #         "\nDUPLICATE CLAUSE FOUND"
            #     )

            #     print(
            #         "Clause:",
            #         clause.clause_no
            #     )

            #     print(
            #         clause.text[:500]
            #     )

            seen.add(
                clause.clause_no
            )

            sub_seen = set()

            for sub in clause.sub_clauses:

                # if sub.sub_clause_no in sub_seen:




                #     errors.append(
                #         f"Duplicate SubClause "
                #         f"{sub.sub_clause_no}"
                #     )




                sub_seen.add(
                    sub.sub_clause_no
                )

                roman_seen = set()

                for roman in sub.roman_clauses:

                    if roman.roman_no in roman_seen:

                        errors.append(
                            f"Duplicate Roman "
                            f"{roman.roman_no}"
                        )

                    roman_seen.add(
                        roman.roman_no
                    )

        return errors


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    with open(
        "../../pdfs/bnss.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()

    cleaner=BNSSTextCleaner()
    text=cleaner.clean(text)

 

    parser = ClauseParser()

    print(len(parser.CLAUSE_RE.findall(text)))
    print(len(parser.SUBCLAUSE_RE.findall(text)))
    print(len(parser.ROMAN_RE.findall(text)))

    clauses = parser.parse_clauses(
        text
    )

    # print(
    #     "Clauses:",
    #     len(clauses)
    # )

    # for clause in clauses:

    #     print(
    #         clause.clause_no,
    #         len(clause.sub_clauses)
    #     )

    print(
        parser.validate_clauses(
            clauses
        )
    )