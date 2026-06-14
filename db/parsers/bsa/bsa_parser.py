from __future__ import annotations

from db.parsers.bsa.cleaner import BSATextCleaner
from db.parsers.bsa.legal_models import (
    LegalDocument
)

from db.parsers.bsa.part_parser import (
    PartParser
)

from db.parsers.bsa.chapter_parser import (
    ChapterParser
)

from db.parsers.bsa.section_parser import (
    SectionParser
)

from db.parsers.bsa.clause_parser import (
    ClauseParser
)

from db.parsers.bsa.explaination_parser import (
    ExplanationParser
)

from db.parsers.bsa.illustration_parser import (
    IllustrationParser
)

from db.parsers.bsa.reference_parser import (
    ReferenceExtractor
)


class BSAParser:

    DOCUMENT_NAME = (
        "Bharatiya Sakshya Adhiniyam, 2023"
    )

    def __init__(self):

        self.part_parser = (
            PartParser()
        )

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

        self.illustration_parser = (
            IllustrationParser()
        )

        self.reference_extractor = (
            ReferenceExtractor()
        )

    # ==================================================
    # PARSE
    # ==================================================

    def parse(
        self,
        text: str
    ) -> LegalDocument:

        document = LegalDocument(
            document=
                self.DOCUMENT_NAME
        )

        # =====================================
        # PARTS
        # =====================================

        parts = (
            self.part_parser
            .extract_parts(text)
        )

        # -------------------------------------
        # BSA without Parts
        # -------------------------------------

        if not parts:

            chapters = (
                self.chapter_parser
                .extract_chapters(text)
            )

            self._parse_chapters(
                chapters
            )

            document.chapters.extend(
                chapters
            )

            return document

        # =====================================
        # PART -> CHAPTER
        # =====================================

        for part in parts:

            chapters = (
                self.chapter_parser
                .extract_chapters(
                    part.text
                )
            )

            self._parse_chapters(
                chapters
            )

            part.chapters.extend(
                chapters
            )

            document.parts.append(
                part
            )

            document.chapters.extend(
                chapters
            )

        return document

    # ==================================================
    # PARSE CHAPTERS
    # ==================================================

    def _parse_chapters(
        self,
        chapters
    ):

        for chapter in chapters:

            sections = (
                self.section_parser
                .extract_sections(
                    chapter.text
                )
            )

            for section in sections:

                # ------------------------------
                # Clauses
                # ------------------------------

                # if section.section_no in ["52", "115", "141"]:

                #     print("=" * 100)
                #     print(section.text[:1500])

                section.clauses.extend(
                    self.clause_parser
                    .parse_clauses(
                        section.text
                    )
                )

                # ------------------------------
                # Explanations
                # ------------------------------

                section.explanations.extend(
                    self.explanation_parser
                    .extract_explanations(
                        section.text
                    )
                )

                # ------------------------------
                # Illustrations
                # ------------------------------

                section.illustrations.extend(
                    self.illustration_parser
                    .extract_illustrations(
                        section.text
                    )
                )

                # ------------------------------
                # References
                # ------------------------------

                section.references.extend(
                    self.reference_extractor
                    .extract_references(
                        section.text,
                        section.section_no
                    )
                )

            chapter.sections.extend(
                sections
            )

    # ==================================================
    # VALIDATION
    # ==================================================

    def validate(
        self,
        document: LegalDocument
    ):

        errors = []

        chapter_seen = set()

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

            section_seen = set()

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
                    self.illustration_parser
                    .validate_illustrations(
                        section.illustrations
                    )
                )

        return errors
    

    


if __name__ == "__main__":

    with open(
        "../../pdfs/bsa.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()

    cleanner=BSATextCleaner()
    text=cleanner.clean(text)


    # for line in text.splitlines():

    #     if "Part" in line.upper():
    #         print(repr(line))



    parser = BSAParser()

    bsa = parser.parse(
        text
    )

    # for target in ["52", "60", "115", "141"]:

    #     for chapter in bsa.chapters:
    #         for section in chapter.sections:

    #             if section.section_no == target:

    #                 print(f"\nSECTION {target}")

    #                 for clause in section.clauses:

    #                     print(
    #                         f"Clause {clause.clause_no}"
    #                     )

    #                     for sub in clause.sub_clauses:

    #                         print(
    #                             f"   Sub {sub.sub_clause_no}"
    #                         )

    #                         for roman in sub.roman_clauses:

    #                             print(
    #                                 f"      Roman {roman.roman_no}"
    #                             )

    print("\n========== BSA STATS ==========\n")

    print(
        "Parts:",
        len(bsa.parts)
    )

    print(
        "Chapters:",
        len(bsa.chapters)
    )

    sections = 0
    clauses = 0
    subclauses = 0
    roman_clauses = 0
    explanations = 0
    illustrations = 0
    references = 0

    for chapter in bsa.chapters:

        sections += len(
            chapter.sections
        )

        for section in chapter.sections:

            clauses += len(
                section.clauses
            )

            explanations += len(
                section.explanations
            )

            illustrations += len(
                section.illustrations
            )

            references += len(
                section.references
            )

            for clause in section.clauses:

                subclauses += len(
                    clause.sub_clauses
                )

                if hasattr(
                    clause,
                    "roman_clauses"
                ):
                    roman_clauses += len(
                        clause.roman_clauses
                    )

                for sub in clause.sub_clauses:

                    roman_clauses += len(
                        sub.roman_clauses
                    )

    print(
        "Sections:",
        sections
    )

    print(
        "Clauses:",
        clauses
    )

    print(
        "SubClauses:",
        subclauses
    )

    print(
        "Roman Clauses:",
        roman_clauses
    )

    print(
        "Explanations:",
        explanations
    )

    print(
        "Illustrations:",
        illustrations
    )

    print(
        "References:",
        references
    )





