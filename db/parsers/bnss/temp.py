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
    NUMERIC_RE = re.compile(
        r'(?m)^\((\d+[A-Z]?)\)'
    )

    ALPHA_RE = re.compile(
        r'(?m)^\(([a-z])\)'
    )

    CAPITAL_RE = re.compile(
        r'(?m)^\(([A-Z])\)'
    )

    ROMAN_RE = re.compile(
        r'(?:(?<=\n)|(?<=;)|(?<=:)|(?<=—)|(?<=\.)|^)\s*\((i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv|xvi|xvii|xviii|xix|xx)\)',
        re.I
    )
    CLAUSE_RE = re.compile(
        r'(?m)^\s*\((\d+[A-Z]?)\)'
    )

    SUBCLAUSE_RE = re.compile(
        r'(?m)^\s*\(([a-z])\)'
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
                    document="bns",
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
    @staticmethod
    def remove_illustrations(
        self,
        text: str
    ):

        return re.split(
            r'Illustrations?\.',
            text,
            maxsplit=1,
            flags=re.I
        )[0]

    def parse_subclauses(
        self,
        text: str
    ) -> List[SubClause]:
        text=self.remove_illustrations(text)
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
                document="bns",
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
    

    def build_alpha_structure(
        self,
        text: str,
        pattern: re.Pattern
    ) -> List[Clause]:

        clause = Clause(
            document="bns",
            clause_no="0",
            text=text
        )

        sections = self.split_sections(
            text,
            pattern
        )

        for sub_no, sub_text in sections:

            sub = SubClause(
                document="bns",
                sub_clause_no=sub_no,
                text=sub_text
            )

            sub.roman_clauses.extend(
                self.parse_roman_clauses(
                    sub_text
                )
            )

            clause.sub_clauses.append(
                sub
            )

        return [clause]
    
    def build_numeric_structure(
        self,
        text: str
    ) -> List[Clause]:

        clauses = []

        clause_sections = self.split_sections(
            text,
            self.NUMERIC_RE
        )

        for clause_no, clause_text in clause_sections:

            clause = Clause(
                document="bns",
                clause_no=clause_no,
                text=clause_text
            )

            alpha_sections = self.split_sections(
                clause_text,
                self.ALPHA_RE
            )

            if alpha_sections:

                for sub_no, sub_text in alpha_sections:

                    sub = SubClause(
                        document="bns",
                        sub_clause_no=sub_no,
                        text=sub_text
                    )

                    sub.roman_clauses.extend(
                        self.parse_roman_clauses(
                            sub_text
                        )
                    )

                    clause.sub_clauses.append(
                        sub
                    )

            clauses.append(
                clause
            )

        return clauses
    def parse_alpha_clauses(
        self,
        text: str
    ):

        return self.build_alpha_structure(
            text,
            self.ALPHA_RE
        )
    

    def parse_alpha_roman(
        self,
        text: str
    ):

        return self.build_alpha_structure(
            text,
            self.ALPHA_RE
        )
    

    def parse_capital_roman(
        self,
        text: str
    ):

        return self.build_alpha_structure(
            text,
            self.CAPITAL_RE
        )


    def parse_numeric_clauses(
        self,
        text: str
    ):

        clauses = []

        sections = self.split_sections(
            text,
            self.NUMERIC_RE
        )

        for clause_no, clause_text in sections:

            clauses.append(
                Clause(
                    document="bns",
                    clause_no=clause_no,
                    text=clause_text
                )
            )

        return clauses

    def parse_numeric_alpha(
        self,
        text: str
    ):

        return self.build_numeric_structure(
            text
        )
    

    def parse_numeric_alpha_roman(
        self,
        text: str
    ):

        return self.build_numeric_structure(
            text
        )




    # =====================================================
    # CLAUSES
    # =====================================================

    def parse_clauses(
        self,
        section_text: str
    ) -> List[Clause]:

        clauses = []

        clause_sections = self.split_sections(
            section_text,
            self.CLAUSE_RE
        )

        # No numbered clauses present
        if not clause_sections:

            subclauses = self.parse_subclauses(
                section_text
            )

            if subclauses:

                synthetic_clause = Clause(
                    document="bns",
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

        for clause_no, clause_text in clause_sections:

            clause = Clause(
                document="bns",
                clause_no=clause_no,
                text=clause_text
            )

            clause.sub_clauses.extend(
                self.parse_subclauses(
                    clause_text
                )
            )
            clause.roman_clauses.extend(
                self.parse_roman_clauses(
                    clause_text
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

        if has_numeric:
            return self.build_numeric_structure(
                section_text
            )

        if has_capital:
            return self.build_alpha_structure(
                section_text,
                self.CAPITAL_RE
            )

        if has_alpha:
            return self.build_alpha_structure(
                section_text,
                self.ALPHA_RE
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

            if clause.clause_no in seen:

                print("\n" + "="*80)
                print("section: ",section_no)
                print("DUPLICATE SUBCLAUSE")
                print("Clause:", clause.clause_no)
                print("SubClause:", sub.sub_clause_no)
                print(sub.text[:1000])

                errors.append(
                    f"Duplicate SubClause "
                    f"{sub.sub_clause_no}"
                )

            seen.add(
                clause.clause_no
            )

            sub_seen = set()

            for sub in clause.sub_clauses:

                if sub.sub_clause_no in sub_seen:

                    errors.append(
                        f"Duplicate SubClause "
                        f"{sub.sub_clause_no}"
                    )

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
        "../../pdfs/bns.txt",
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

    clauses = parser.parse_section_structure(
        text
    )

    print(
        "Clauses:",
        len(clauses)
    )

    # for clause in clauses:

    #     print(
    #         clause.clause_no,
    #         len(clause.sub_clauses)
    #     )

    # print(
    #     parser.validate_clauses(
    #         clauses
    #     )
    # )