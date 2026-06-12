from __future__ import annotations

from chapter_parser import ChapterParser
from section_parser import SectionParser
from clause_parser import ClauseParser
from explanation_parser import ExplanationParser
from reference_extractor import ReferenceExtractor
from cleaner import BNSTextCleaner
import re
from legal_models import (
    BNSDocument,
    Chapter,
    Section
)


class BNSParser:

    """
    Main Bharatiya Nyaya Sanhita Parser

    Pipeline:

        BNS
            ↓
        Chapters
            ↓
        Sections
            ↓
        Clauses
            ↓
        Explanations
            ↓
        References
    """
    
    def __init__(self):

        self.chapter_parser = (
            ChapterParser()
        )

        self.section_parser = (
            SectionParser()
        )

        self.clause_parser = (
            ClauseParser()
        )

        self.explanation_parser = (
            ExplanationParser()
        )

        self.reference_extractor = (
            ReferenceExtractor()
        )

    @staticmethod
    def normalize_bns_text(text):

        text = re.sub(
            r'(\d+)\.\s*\((\d+)\)',
            r'\1.\n(\2)',
            text
        )

        return text

    # =====================================================
    # PARSE
    # =====================================================

    def parse(
        self,
        text: str
    ) -> BNSDocument:
        
        # text=self.normalize_bns_text(text)

        document = (
            BNSDocument()
        )

        chapters = (
            self.chapter_parser
            .extract_chapters(text)
        )

        for chapter_dict in chapters:

            chapter = Chapter(
                document="bns",
                chapter_no=
                    chapter_dict[
                        "chapter_no"
                    ],

                chapter_title=
                    chapter_dict[
                        "chapter_title"
                    ],

                text=
                    chapter_dict[
                        "text"
                    ]
            )

            sections = (
                self.section_parser
                .extract_sections(
                    chapter.text
                )
            )

            for section_dict in sections:

                section = Section(
                    document="bns",

                    section_no=
                        section_dict[
                            "section_no"
                        ],

                    section_title=
                        section_dict[
                            "section_title"
                        ],

                    text=
                        section_dict[
                            "text"
                        ]
                )

                # ==========================
                # CLAUSES
                # ==========================

                section.clauses.extend(
                    self.clause_parser.parse_clauses(
                        section.text
                    )
                )

                # ==========================
                # EXPLANATIONS
                # ==========================

                section.explanations.extend(
                    self.explanation_parser
                    .extract_explanations(
                        section.text
                    )
                )

                # ==========================
                # REFERENCES
                # ==========================

                section.references.extend(
                    self.reference_extractor
                    .extract_references(
                        text=
                            section.text,

                        source_section=
                            section.section_no
                    )
                )

                chapter.sections.append(
                    section
                )

            document.chapters.append(
                chapter
            )
            
        return document

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate(
        self,
        document: BNSDocument
    ):

        errors = []

        chapter_seen = set()

        section_seen = set()

        for chapter in document.chapters:

            if (
                chapter.chapter_no
                in chapter_seen
            ):

                errors.append(
                    f"Duplicate Chapter "
                    f"{chapter.chapter_no}"
                )

            chapter_seen.add(
                chapter.chapter_no
            )

            for section in chapter.sections:

                if (
                    section.section_no
                    in section_seen
                ):

                    errors.append(
                        f"Duplicate Section "
                        f"{section.section_no}"
                    )

                section_seen.add(
                    section.section_no
                )

                errors.extend(
                    self.clause_parser
                    .validate_clauses(
                        section.clauses
                    )
                )

                errors.extend(
                    self.explanation_parser
                    .validate_explanations(
                        section.explanations
                    )
                )

                errors.extend(
                    self.reference_extractor
                    .validate_references(
                        section.references
                    )
                )

        return errors

    # =====================================================
    # STATS
    # =====================================================

    def stats(
        self,
        document: BNSDocument
    ):

        chapter_count = (
            len(document.chapters)
        )

        section_count = 0
        clause_count = 0
        subclause_count = 0
        roman_count = 0
        explanation_count = 0
        reference_count = 0

        for chapter in document.chapters:

            section_count += (
                len(chapter.sections)
            )

            for section in chapter.sections:

                explanation_count += (
                    len(
                        section.explanations
                    )
                )

                reference_count += (
                    len(
                        section.references
                    )
                )

                clause_count += (
                    len(
                        section.clauses
                    )
                )

                for clause in (
                    section.clauses
                ):

                    subclause_count += (
                        len(
                            clause.sub_clauses
                        )
                    )

                    for sub in (
                        clause.sub_clauses
                    ):

                        roman_count += (
                            len(
                                sub.roman_clauses
                            )
                        )

        return {
            "chapters":
                chapter_count,

            "sections":
                section_count,

            "clauses":
                clause_count,

            "subclauses":
                subclause_count,

            "roman_clauses":
                roman_count,

            "explanations":
                explanation_count,

            "references":
                reference_count
        }


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

    cleanner=BNSTextCleaner()
    text=cleanner.clean(text)


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
        r'(?m)^\((i|ii|iii|iv|v|vi|vii|viii|ix|x|xi|xii|xiii|xiv|xv)\)',
        re.I
    )
    



    parser = BNSParser()

    bns = parser.parse(
        text
    )

    # for chapter in bns.chapters:

    #     for section in chapter.sections:

    #         has_numeric = bool(
    #             NUMERIC_RE.search(section.text)
    #         )

    #         has_alpha = bool(
    #             ALPHA_RE.search(section.text)
    #         )

    #         has_capital = bool(
    #             CAPITAL_RE.search(section.text)
    #         )

    #         has_roman = bool(
    #             ROMAN_RE.search(section.text)
    #         )

    #         if (
    #             has_numeric
    #             or has_alpha
    #             or has_capital
    #             or has_roman
    #         ):

    #             print("\n" + "=" * 80)

    #             print(
    #                 f"Section {section.section_no}"
    #             )

    #             print(
    #                 f"Numeric: {has_numeric}"
    #             )

    #             print(
    #                 f"Alpha: {has_alpha}"
    #             )

    #             print(
    #                 f"Capital: {has_capital}"
    #             )

    #             print(
    #                 f"Roman: {has_roman}"
    #             )

    #             print(
    #                 section.text[:1000])




    # def detect_structure(text):

    #     return {
    #         "numeric": bool(NUMERIC_RE.search(text)),
    #         "alpha": bool(ALPHA_RE.search(text)),
    #         "capital": bool(CAPITAL_RE.search(text)),
    #         "roman": bool(ROMAN_RE.search(text)),
    #     }

    # from collections import Counter

    # counter = Counter()

    # for chapter in bns.chapters:
    #     for section in chapter.sections:

    #         s = detect_structure(section.text)

    #         key = (
    #             s["numeric"],
    #             s["alpha"],
    #             s["capital"],
    #             s["roman"]
    #         )

    #         counter[key] += 1

    # print(counter)



    # for chapter in bns.chapters:

    #     for section in chapter.sections:

    #         has_numeric = bool(
    #             re.search(
    #                 r'(?m)^\((\d+[A-Z]?)\)',
    #                 section.text
    #             )
    #         )

    #         has_alpha = bool(
    #             re.search(
    #                 r'(?m)^\(([a-z])\)',
    #                 section.text
    #             )
    #         )

    #         has_capital = bool(
    #             re.search(
    #                 r'(?m)^\(([A-Z])\)',
    #                 section.text
    #             )
    #         )

    #         has_roman = bool(
    #             re.search(
    #                 r'(?m)^\(([ivxlcdm]+)\)',
    #                 section.text,
    #                 re.I
    #             )
    #         )

    #         if sum([
    #             has_numeric,
    #             has_alpha,
    #             has_capital,
    #             has_roman
    #         ]) > 1:

    #             print(
    #                 section.section_no,
    #                 has_numeric,
    #                 has_alpha,
    #                 has_capital,
    #                 has_roman
    #             )
    
    

    stats = parser.stats(
        bns
    )

    print()

    print(
        "========== BNS STATS =========="
    )

    print()

    for k, v in stats.items():

        print(
            f"{k}: {v}"
        )

    print()

    errors = parser.validate(
        bns
    )

    print(
        "Errors:",
        len(errors)
    )

    for e in errors[:20]:

        print(e)