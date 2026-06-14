
from __future__ import annotations

import re
from typing import List

from db.parsers.consitution.legal_models import (
    Clause,
    SubClause,
    RomanClause
)


class ClauseParser:

    """
    Recursive Clause Parser

    Handles:

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
        (xiv)

    """

    # =====================================================
    # REGEX
    # =====================================================

    CLAUSE_RE = re.compile(
        r"(?m)^\((\d+[A-Z]?)\)\s"
    )

    SUBCLAUSE_RE = re.compile(
        r"""
        ^\(
        ([a-hj-z])
        \)
        \s
        """,
        re.MULTILINE
        | re.VERBOSE
    )

    ROMAN_RE = re.compile(
        r"""
        ^\(
        (
            i|ii|iii|iv|v|vi|vii|viii|ix|
            x|xi|xii|xiii|xiv|xv|
            xvi|xvii|xviii|xix|xx
        )
        \)
        \s
        """,
        re.MULTILINE
        | re.IGNORECASE
        | re.VERBOSE
    )

    # =====================================================
    # SPLIT BY MARKER
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

        for roman_no, roman_text in self.split_sections(
            text,
            self.ROMAN_RE
        ):

            romans.append(
                RomanClause(
                    document="constitution",
                    roman_no=roman_no,
                    text=roman_text
                )
            )

        return romans

    # =====================================================
    # SUB CLAUSES
    # =====================================================

    def parse_subclauses(
        self,
        text: str
    ) -> List[SubClause]:

        subclauses = []

        for sub_no, sub_text in self.split_sections(
            text,
            self.SUBCLAUSE_RE
        ):

            sub = SubClause(
                document="constitution",
                sub_clause_no=sub_no,
                text=sub_text
            )

            sub.roman_clauses.extend(
                self.parse_roman_clauses(
                    sub_text
                )
            )

            subclauses.append(sub)

        return subclauses
    
    @staticmethod
    def clean_constitution_text(text: str) -> str:

        # footnotes
        text = re.sub(
            r'(?m)^\d+\.\s+(Subs\.|Ins\.|Omitted|Added|Inserted).*?$',
            '',
            text
        )

        # page separators
        text = re.sub(
            r'_{5,}',
            '',
            text
        )

        # page numbers
        text = re.sub(
            r'(?m)^\d+\s*$',
            '',
            text
        )

        # amendment markers
        text = re.sub(
            r'\d+\[',
            '',
            text
        )

        return text

    @staticmethod
    def remove_footnotes(text: str) -> str:

        text = re.sub(
            r"(?im)^\s*\d+\s+(Subs\.|Ins\.|Omitted|Added|Inserted).*?$",
            "",
            text
        )

        text = re.sub(
            r"(?im)^\s*\d+\s+Vide.*?$",
            "",
            text
        )

        text = re.sub(
            r"(?im)^\s*\d+\s+The words.*?$",
            "",
            text
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text

    # =====================================================
    # CLAUSES
    # =====================================================

    def parse_clauses(
        self,
        article_text: str
    ) -> List[Clause]:
        article_text=self.clean_constitution_text(article_text)
        article_text=self.remove_footnotes(article_text)
        clauses = []

        clause_sections = self.split_sections(
            article_text,
            self.CLAUSE_RE
        )

        if not clause_sections:
            return clauses

        for clause_no, clause_text in clause_sections:

            clause = Clause(
                document="constitution",
                clause_no=clause_no,
                text=clause_text
            )

            clause.sub_clauses.extend(
                self.parse_subclauses(
                    clause_text
                )
            )

            clauses.append(clause)

        return clauses

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_clauses(
        self,
        clauses: List[Clause]
    ) -> List[str]:

        errors = []

        seen = set()

        for clause in clauses:

            if clause.clause_no in seen:

                errors.append(
                    f"Duplicate Clause "
                    f"{clause.clause_no}"
                )

            seen.add(
                clause.clause_no
            )

            sub_seen = set()

            for sub in clause.sub_clauses:

                if sub.sub_clause_no in sub_seen:

                    errors.append(
                        f"Duplicate SubClause "
                        f"{sub.sub_clause_no} "
                        f"in Clause "
                        f"{clause.clause_no}"
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
# EXAMPLE
# =========================================================


def get_clause_stats(
    
    clauses
):
    return {
        "clauses":
            len(clauses),

        "subclauses":
            sum(
                len(c.sub_clauses)
                for c in clauses
            ),

        "roman":
            sum(
                len(
                    s.roman_clauses
                )
                for c in clauses
                for s in c.sub_clauses
            )
    }



if __name__ == "__main__":

    with open(
        "../../pdfs/constitution.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()

    parser = ClauseParser()

    clauses = parser.parse_clauses(
        text
    )
    

    # print(
    #     f"Clauses: "
    #     f"{len(clauses)}"
    # )

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
