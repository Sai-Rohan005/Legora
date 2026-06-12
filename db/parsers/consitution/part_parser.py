
from __future__ import annotations

import re
from typing import List, Dict


class PartParser:

    """
    Constitution Part Parser

    Handles:

        PART I
        PART IXA
        PART IXB
        PART XIVA

    Ignores:

        Part A States
        Part B States
        Schedule references
        Appendix references
    """

    VALID_PARTS = {
        "I", "II", "III", "IV", "IVA",
        "V", "VI", "VII", "VIII",
        "IX", "IXA", "IXB",
        "X", "XI", "XII", "XIII",
        "XIV", "XIVA",
        "XV", "XVI", "XVII",
        "XVIII", "XIX", "XX",
        "XXI", "XXII"
    }

    PART_RE = re.compile(
        r"(?im)^\s*PART\s+([IVXLCDM]+(?:[A-Z])?)\s*$"
    )

    # =====================================================
    # CLEAN
    # =====================================================

    @staticmethod
    def clean_text(text: str) -> str:

        # footnotes

        text = re.sub(
            r"(?im)^\s*\d+\.\s+(Subs\.|Ins\.|Omitted|Added|Inserted).*?$",
            "",
            text
        )

        text = re.sub(
            r"(?im)^\s*\d+\.\s+Vide.*?$",
            "",
            text
        )

        text = re.sub(
            r"(?im)^\s*\d+\.\s+The words.*?$",
            "",
            text
        )

        # page separators

        text = re.sub(
            r"_{5,}",
            "",
            text
        )

        # page numbers

        text = re.sub(
            r"(?m)^\s*\d+\s*$",
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
    # CUT AFTER MAIN CONSTITUTION
    # =====================================================

    @staticmethod
    def cut_before_schedules(
        text: str
    ) -> str:

        match = re.search(
            r"(?im)^FIRST\s+SCHEDULE\s*$",
            text
        )
        appendix_match = re.search(
            r"(?im)^\s*APPENDIX\s+I\b",
            text
        )

        if appendix_match:
            cutoff = appendix_match.start()

        elif match:
            cutoff = match.start()

        else:
            cutoff = None

        if cutoff:
            text = text[:cutoff]

        if match:
            return text[:match.start()]

        return text

    # =====================================================
    # TITLE EXTRACTION
    # =====================================================

    def extract_part_title(
        self,
        text: str,
        start: int
    ) -> str:

        chunk = text[
            start:start + 250
        ]

        lines = [
            line.strip()
            for line in chunk.split("\n")
            if line.strip()
        ]

        if len(lines) < 2:
            return ""

        for line in lines[1:]:

            if re.match(
                r"^\d+[A-Z]{0,3}\.",
                line
            ):
                break

            if re.match(
                r"^PART\s+",
                line,
                re.I
            ):
                break

            if re.match(
                r"^CHAPTER\s+",
                line,
                re.I
            ):
                break

            if (
                "CONSTITUTION OF INDIA"
                in line.upper()
            ):
                continue

            if len(line.split()) > 20:
                continue

            if len(line) > 200:
                continue

            return line

        return ""

    # =====================================================
    # EXTRACT
    # =====================================================

    def extract_parts(
        self,
        text: str
    ) -> List[Dict]:

        text = self.clean_text(text)

        text = self.cut_before_schedules(
            text
        )

        matches = list(
            self.PART_RE.finditer(text)
        )
        


        parts = []

        for i, match in enumerate(
            matches
        ):

            part_no = (
            match.group(1)
            .replace("-", "")
            .replace(" ", "")
            .upper()
        )

            if (
                part_no
                not in self.VALID_PARTS
            ):
                continue

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            part_title = (
                self.extract_part_title(
                    text,
                    start
                )
            )

            part_text = (
                text[start:end]
                .strip()
            )

            parts.append(
                {
                    "part_no":
                        part_no,

                    "part_title":
                        part_title,

                    "text":
                        part_text,

                    "start":
                        start,

                    "end":
                        end
                }
            )

        return parts

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_parts(
        self,
        parts: List[Dict]
    ) -> List[str]:

        errors = []

        seen = set()

        for part in parts:

            part_no = (
                part["part_no"]
            )

            if part_no in seen:

                errors.append(
                    f"Duplicate Part "
                    f"{part_no}"
                )

            seen.add(part_no)

            if not (
                part["part_title"]
            ):

                errors.append(
                    f"Missing title "
                    f"for Part "
                    f"{part_no}"
                )

        return errors


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    with open(
        "../../pdfs/constitution.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()





    parser = PartParser()

    parts = parser.extract_parts(
        text
    )

    print(
        f"Parts Found: "
        f"{len(parts)}"
    )

    print()

    for part in parts:

        print(
            f"{part['part_no']} "
            f"-> "
            f"{part['part_title']}"
        )
