from __future__ import annotations

from db.parsers.bns.chapter_parser import ChapterParser
from db.parsers.bns.section_parser import SectionParser
from db.parsers.bns.clause_parser import ClauseParser
from db.parsers.bns.explanation_parser import ExplanationParser
from db.parsers.bns.reference_extractor import ReferenceExtractor
from db.parsers.bns.cleaner import BNSTextCleaner
import re
from db.parsers.bns.legal_models import (
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
                        section.section_no,
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
    
    # for m in re.finditer(r"\(\d+[A-Za-z]?\)", text):

    #     start = max(0, m.start() - 60)
    #     end = min(len(text), m.end() + 100)

    #     context = text[start:end]

    #     if "\n" not in text[max(0, m.start()-5):m.start()]:

    #         print("=" * 80)
    #         print(context)


    parser = BNSParser()

    bns = parser.parse(
        text
    )

    # for chapter in bns.chapters:
    #     for section in chapter.sections:

    #         if "(a)" in section.text:

    #             total_subs = sum(
    #                 len(c.sub_clauses)
    #                 for c in section.clauses
    #             )

    #             if total_subs == 0:

    #                 print(
    #                     "\nSECTION:",
    #                     section.section_no
    #                 )

    #                 print(
    #                     section.text[:2000]
    #                 )
    

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