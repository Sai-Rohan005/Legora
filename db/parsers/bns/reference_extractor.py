from __future__ import annotations

import re
from typing import List


class ReferenceExtractor:

    """
    BNS Reference Extractor

    Detects:

        section 103

        Section 103

        sections 103 and 104

        sections 103, 104, 105

        section 103 of this Sanhita
    """

    # =====================================================
    # SECTION REFERENCES
    # =====================================================

    SECTION_RE = re.compile(
        r"\bsection[s]?\s+([0-9,\sand]+)",
        re.IGNORECASE
    )

    NUMBER_RE = re.compile(
        r"\d+"
    )

    # =====================================================
    # EXTRACT REFERENCES
    # =====================================================

    def extract_references(
        self,
        text: str,
        source_section: str
    ) -> List[dict]:

        references = []

        matches = (
            self.SECTION_RE.finditer(
                text
            )
        )

        for match in matches:

            raw = match.group(1)

            targets = (
                self.NUMBER_RE.findall(
                    raw
                )
            )

            for target in targets:

                references.append(
                    {
                        "source_section":
                            source_section,

                        "target_section":
                            target,

                        "reference_type":
                            "section"
                    }
                )

        return references

    # =====================================================
    # UNIQUE REFERENCES
    # =====================================================

    def unique_references(
        self,
        refs: List[dict]
    ) -> List[dict]:

        seen = set()

        unique = []

        for ref in refs:

            key = (
                ref["source_section"],
                ref["target_section"]
            )

            if key in seen:
                continue

            seen.add(key)

            unique.append(ref)

        return unique

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_references(
        self,
        refs: List[dict]
    ) -> List[str]:

        errors = []

        for ref in refs:

            if (
                ref["source_section"]
                ==
                ref["target_section"]
            ):

                errors.append(
                    f"Self reference "
                    f"Section "
                    f"{ref['source_section']}"
                )

        return errors


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    sample = """
Whoever commits murder under section 103
shall be punished.

The provisions of sections 63 and 64
shall also apply.

Nothing in section 111 shall affect
the operation of this section.
"""

    extractor = (
        ReferenceExtractor()
    )

    refs = (
        extractor.extract_references(
            text=sample,
            source_section="104"
        )
    )

    refs = (
        extractor.unique_references(
            refs
        )
    )

    print(
        "References:",
        len(refs)
    )

    print()

    for r in refs:

        print(r)

    print()

    errors = (
        extractor.validate_references(
            refs
        )
    )

    print(
        "Errors:",
        len(errors)
    )