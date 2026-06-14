from __future__ import annotations

import re
from typing import List

from db.parsers.bsa.cleaner import BSATextCleaner
from db.parsers.bsa.legal_models import Section


class SectionParser:

    """
    Bharatiya Sakshya Adhiniyam Section Parser
    """

    # =====================================================
    # SECTION HEADER
    # =====================================================

    SECTION_RE = re.compile(
        r"(?m)^(\d{1,3})\.\s+(.+)$"
    )

    SECTION_NO_RE = re.compile(
        r"^\d+$"
    )

    # =====================================================
    # CLEAN TITLE
    # =====================================================

    @staticmethod
    def clean_title(
        title: str
    ) -> str:

        title = title.strip()

        title = re.sub(
            r"\s+",
            " ",
            title
        )

        title = title.strip(
            ".-— "
        )

        return title

    # =====================================================
    # RECOVER TITLE
    # =====================================================

    def recover_title(
        self,
        section_text: str,
        current_title: str
    ) -> str:

        if current_title:

            return self.clean_title(
                current_title
            )

        lines = [
            x.strip()
            for x in section_text.split("\n")
            if x.strip()
        ]

        if len(lines) < 2:
            return ""

        return self.clean_title(
            lines[1]
        )

    # =====================================================
    # REMOVE STATEMENT OF OBJECTS
    # =====================================================

    @staticmethod
    def remove_statement_of_objects(
        text: str
    ) -> str:

        marker = (
            "The Commission suggested various enactments"
        )

        idx = text.find(
            marker
        )

        if idx != -1:

            text = text[:idx]

        return text

    # =====================================================
    # EXTRACT SECTIONS
    # =====================================================

    def extract_sections(
        self,
        text: str
    ) -> List[Section]:

        text = (
            self.remove_statement_of_objects(
                text
            )
        )

        matches = list(
            self.SECTION_RE.finditer(
                text
            )
        )

        if not matches:
            return []

        sections = []

        for i, match in enumerate(
            matches
        ):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            section_no = (
                match.group(1)
                .strip()
            )

            section_title = (
                match.group(2)
                .strip()
            )

            section_text = (
                text[start:end]
                .strip()
            )

            section_title = (
                self.recover_title(
                    section_text,
                    section_title
                )
            )

            sections.append(
                Section(
                    document="bsa",

                    section_no=
                        section_no,

                    title=
                        section_title,

                    text=
                        section_text
                )
            )

        return sections

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_sections(
        self,
        sections: List[Section]
    ) -> List[str]:

        errors = []

        seen = set()

        for section in sections:

            section_no = (
                section.section_no
            )

            if section_no in seen:

                errors.append(
                    f"Duplicate Section "
                    f"{section_no}"
                )

            seen.add(
                section_no
            )

            if not self.SECTION_NO_RE.match(
                section_no
            ):

                errors.append(
                    f"Invalid Section "
                    f"{section_no}"
                )

            if not section.title:

                errors.append(
                    f"Missing title for "
                    f"Section {section_no}"
                )

        return errors

    # =====================================================
    # GET SECTION
    # =====================================================

    def get_section(
        self,
        sections: List[Section],
        section_no: str
    ):

        for section in sections:

            if (
                section.section_no
                == section_no
            ):

                return section

        return None


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    with open(
        "../../pdfs/bsa.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()

    cleaner = BSATextCleaner()

    text = cleaner.clean(
        text
    )

    parser = SectionParser()

    sections = (
        parser.extract_sections(
            text
        )
    )

    print(
        f"Sections Found: "
        f"{len(sections)}"
    )

    print()

    for section in sections[:20]:

        print(
            f"{section.section_no}"
            f" -> "
            f"{section.title}"
        )

    print()

    errors = (
        parser.validate_sections(
            sections
        )
    )

    print(
        f"Errors: "
        f"{len(errors)}"
    )

    for error in errors:

        print(error)