
from __future__ import annotations

import re
from typing import List

from db.parsers.consitution.legal_models import Reference


class ReferenceExtractor:

    """
    Extract legal references from Constitution text.

    Supports:

        Article 21
        Article 21A
        Articles 14, 19 and 21

        Part III

        Chapter IV

        Seventh Schedule

        Clause (2)

        Sub-clause (a)
    """

    # =====================================================
    # ARTICLE REFERENCES
    # =====================================================

    ARTICLE_RE = re.compile(
        r"""
        Articles?
        \s+
        (
            [\dA-Z,\-\sandto]+
        )
        """,
        re.IGNORECASE
        | re.VERBOSE
    )

    # =====================================================
    # PART REFERENCES
    # =====================================================

    PART_RE = re.compile(
        r"""
        Part
        \s+
        ([IVXLCDM]+)
        """,
        re.IGNORECASE
        | re.VERBOSE
    )

    # =====================================================
    # CHAPTER REFERENCES
    # =====================================================

    CHAPTER_RE = re.compile(
        r"""
        Chapter
        \s+
        ([IVXLCDM]+)
        """,
        re.IGNORECASE
        | re.VERBOSE
    )

    # =====================================================
    # SCHEDULE REFERENCES
    # =====================================================

    SCHEDULE_RE = re.compile(
        r"""
        (
            First
            |Second
            |Third
            |Fourth
            |Fifth
            |Sixth
            |Seventh
            |Eighth
            |Ninth
            |Tenth
            |Eleventh
            |Twelfth
        )

        \s+
        Schedule
        """,
        re.IGNORECASE
        | re.VERBOSE
    )

    # =====================================================
    # CLAUSE REFERENCES
    # =====================================================

    CLAUSE_RE = re.compile(
        r"""
        Clause
        \s*
        \(
        (\d+[A-Z]?)
        \)
        """,
        re.IGNORECASE
        | re.VERBOSE
    )

    # =====================================================
    # SUBCLAUSE REFERENCES
    # =====================================================

    SUBCLAUSE_RE = re.compile(
        r"""
        Sub[\-\s]?
        Clause
        \s*
        \(
        ([a-z])
        \)
        """,
        re.IGNORECASE
        | re.VERBOSE
    )

    # =====================================================
    # ARTICLE PARSER
    # =====================================================

    def extract_articles(
        self,
        text: str
    ) -> List[Reference]:

        refs = []

        matches = (
            self.ARTICLE_RE.finditer(
                text
            )
        )

        for match in matches:

            raw = match.group(1)

            articles = re.findall(
                r"\d+[A-Z]{0,3}",
                raw
            )

            for article_no in articles:

                refs.append(
                    Reference(
                        reference_type="ARTICLE",
                        reference_value=article_no,
                        text=match.group(0)
                    )
                )

        return refs

    # =====================================================
    # PARTS
    # =====================================================

    def extract_parts(
        self,
        text: str
    ) -> List[Reference]:

        refs = []

        for match in self.PART_RE.finditer(
            text
        ):

            refs.append(
                Reference(
                    reference_type="PART",
                    reference_value=match.group(1),
                    text=match.group(0)
                )
            )

        return refs

    # =====================================================
    # CHAPTERS
    # =====================================================

    def extract_chapters(
        self,
        text: str
    ) -> List[Reference]:

        refs = []

        for match in self.CHAPTER_RE.finditer(
            text
        ):

            refs.append(
                Reference(
                    reference_type="CHAPTER",
                    reference_value=match.group(1),
                    text=match.group(0)
                )
            )

        return refs

    # =====================================================
    # SCHEDULES
    # =====================================================

    def extract_schedules(
        self,
        text: str
    ) -> List[Reference]:

        refs = []

        for match in self.SCHEDULE_RE.finditer(
            text
        ):

            refs.append(
                Reference(
                    reference_type="SCHEDULE",
                    reference_value=match.group(1).upper(),
                    text=match.group(0)
                )
            )

        return refs

    # =====================================================
    # CLAUSES
    # =====================================================

    def extract_clauses(
        self,
        text: str
    ) -> List[Reference]:

        refs = []

        for match in self.CLAUSE_RE.finditer(
            text
        ):

            refs.append(
                Reference(
                    reference_type="CLAUSE",
                    reference_value=match.group(1),
                    text=match.group(0)
                )
            )

        return refs

    # =====================================================
    # SUB CLAUSES
    # =====================================================

    def extract_subclauses(
        self,
        text: str
    ) -> List[Reference]:

        refs = []

        for match in self.SUBCLAUSE_RE.finditer(
            text
        ):

            refs.append(
                Reference(
                    reference_type="SUBCLAUSE",
                    reference_value=match.group(1),
                    text=match.group(0)
                )
            )

        return refs

    # =====================================================
    # MAIN EXTRACTION
    # =====================================================

    def extract(
        self,
        text: str
    ) -> List[Reference]:

        refs = []

        refs.extend(
            self.extract_articles(
                text
            )
        )

        refs.extend(
            self.extract_parts(
                text
            )
        )

        refs.extend(
            self.extract_chapters(
                text
            )
        )

        refs.extend(
            self.extract_schedules(
                text
            )
        )

        refs.extend(
            self.extract_clauses(
                text
            )
        )

        refs.extend(
            self.extract_subclauses(
                text
            )
        )

        return refs

    # =====================================================
    # REMOVE DUPLICATES
    # =====================================================

    def deduplicate(
        self,
        refs: List[Reference]
    ) -> List[Reference]:

        seen = set()

        unique = []

        for ref in refs:

            key = (
                ref.reference_type,
                ref.reference_value
            )

            if key in seen:
                continue

            seen.add(key)

            unique.append(ref)

        return unique


# =========================================================
# EXAMPLE
# =========================================================

if __name__ == "__main__":

    sample = """
    Subject to Article 368.

    Articles 14, 19 and 21.

    Under Part III.

    See Chapter IV.

    Refer Seventh Schedule.

    Clause (2).

    Sub-Clause (a).
    """

    extractor = ReferenceExtractor()

    refs = extractor.extract(
        sample
    )

    refs = extractor.deduplicate(
        refs
    )

    for ref in refs:

        print(
            ref.reference_type,
            ref.reference_value
        )
