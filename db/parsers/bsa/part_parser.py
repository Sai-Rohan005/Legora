from __future__ import annotations

import re
from typing import List

from db.parsers.bsa.legal_models import Part


class PartParser:

    """
    Supports:

    PART I
    PRELIMINARY

    PART II
    RELEVANCY OF FACTS

    PART III
    FACTS WHICH NEED NOT BE PROVED
    """

    # ==========================================
    # PART HEADER
    # ==========================================

    PART_RE = re.compile(
        r"(?im)^PART\s+([IVXLCDM0-9A-Z]+)\s*$"
    )

    # ==========================================
    # EXTRACT PARTS
    # ==========================================

    def extract_parts(
        self,
        text: str
    ) -> List[Part]:

        matches = list(
            self.PART_RE.finditer(
                text
            )
        )

        if not matches:
            return []

        parts = []

        for i, match in enumerate(
            matches
        ):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            block = (
                text[start:end]
                .strip()
            )

            lines = [
                line.strip()
                for line in block.splitlines()
                if line.strip()
            ]

            part_no = (
                match.group(1)
            )

            title = ""

            if len(lines) >= 2:
                title = lines[1]

            parts.append(
                Part(
                    document="bsa",
                    part_no=part_no,
                    title=title,
                    text=block
                )
            )

        return parts

    # ==========================================
    # VALIDATION
    # ==========================================

    def validate_parts(
        self,
        parts: List[Part]
    ) -> List[str]:

        errors = []

        seen = set()

        for part in parts:

            if part.part_no in seen:

                errors.append(
                    f"Duplicate Part "
                    f"{part.part_no}"
                )

            seen.add(
                part.part_no
            )

            if not part.title:

                errors.append(
                    f"Part {part.part_no} "
                    f"missing title"
                )

        return errors
    
if __name__ == "__main__":

    sample = """
PART I
PRELIMINARY

1. Short title.

PART II
RELEVANCY OF FACTS

2. Evidence may be given.
"""

    parser = PartParser()

    parts = parser.extract_parts(
        sample
    )

    for part in parts:

        print(
            part.part_no,
            part.title
        )