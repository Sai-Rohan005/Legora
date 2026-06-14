
from __future__ import annotations

import re
from typing import List, Dict

from db.parsers.consitution.legal_models import (
    Schedule,
    ScheduleParagraph
)


class ScheduleParser:

    """
    Constitution Schedule Parser

    Supports:

        FIRST SCHEDULE
        SECOND SCHEDULE
        THIRD SCHEDULE
        ...
        TWELFTH SCHEDULE
    """

    # =====================================================
    # SCHEDULE DETECTOR
    # =====================================================

    SCHEDULE_RE = re.compile(
        r"""
        ^
        (
            FIRST
            |SECOND
            |THIRD
            |FOURTH
            |FIFTH
            |SIXTH
            |SEVENTH
            |EIGHTH
            |NINTH
            |TENTH
            |ELEVENTH
            |TWELFTH
        )

        \s+

        SCHEDULE
        \s*$
        """,
        re.IGNORECASE
        | re.MULTILINE
        | re.VERBOSE
    )

    # =====================================================
    # PARAGRAPHS
    # =====================================================

    PARAGRAPH_RE = re.compile(
        r"(?m)^\s*(\d+)\.\s"
    )

    # =====================================================
    # CLEAN
    # =====================================================

    def clean_text(
        self,
        text: str
    ) -> str:

        text = text.strip()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text

    # =====================================================
    # EXTRACT TITLE
    # =====================================================

    def extract_schedule_title(
        self,
        schedule_text: str
    ) -> str:

        lines = [
            line.strip()
            for line in schedule_text.split(
                "\n"
            )
            if line.strip()
        ]

        if len(lines) < 2:
            return ""

        title_lines = []

        for line in lines[1:8]:

            if re.match(
                r"^\d+\.",
                line
            ):
                break

            title_lines.append(
                line
            )

        return self.clean_text(
            " ".join(title_lines)
        )

    # =====================================================
    # PARAGRAPHS
    # =====================================================

    def parse_paragraphs(
        self,
        schedule_text: str
    ) -> List[ScheduleParagraph]:

        paragraphs = []

        matches = list(
            self.PARAGRAPH_RE.finditer(
                schedule_text
            )
        )

        if not matches:
            return paragraphs

        for i, match in enumerate(
            matches
        ):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(schedule_text)
            )

            para_no = match.group(1)

            para_text = (
                schedule_text[start:end]
                .strip()
            )

            paragraphs.append(
                ScheduleParagraph(
                    document="constitution",
                    paragraph_no=para_no,
                    text=para_text
                )
            )

        return paragraphs

    # =====================================================
    # EXTRACT SCHEDULES
    # =====================================================

    def extract_schedules(
        self,
        text: str
    ) -> List[Schedule]:

        matches = list(
            self.SCHEDULE_RE.finditer(
                text
            )
        )

        schedules = []

        if not matches:
            return schedules

        for i, match in enumerate(
            matches
        ):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            schedule_no = (
                match.group(1)
                .upper()
            )

            schedule_text = (
                text[start:end]
                .strip()
            )

            schedule_title = (
                self.extract_schedule_title(
                    schedule_text
                )
            )

            schedule = Schedule(
                document="constitution",
                schedule_no=schedule_no,
                schedule_title=schedule_title,
                text=schedule_text
            )

            schedule.paragraphs.extend(
                self.parse_paragraphs(
                    schedule_text
                )
            )

            schedules.append(
                schedule
            )

        return schedules

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_schedules(
        self,
        schedules: List[Schedule]
    ) -> List[str]:

        errors = []

        seen = set()

        for schedule in schedules:

            if schedule.schedule_no in seen:

                errors.append(
                    f"Duplicate Schedule "
                    f"{schedule.schedule_no}"
                )

            seen.add(
                schedule.schedule_no
            )

            if not schedule.schedule_title:

                errors.append(
                    f"Missing Title "
                    f"for Schedule "
                    f"{schedule.schedule_no}"
                )

        return errors


# =========================================================
# EXAMPLE
# =========================================================

if __name__ == "__main__":

    sample = """
FIRST SCHEDULE

THE STATES

1. Andhra Pradesh

2. Telangana

3. Karnataka

SECOND SCHEDULE

SALARIES

1. President

2. Governors
"""

    parser = ScheduleParser()

    schedules = (
        parser.extract_schedules(
            sample
        )
    )

    print(
        f"Schedules Found: "
        f"{len(schedules)}"
    )

    for sch in schedules:

        print()

        print(
            sch.schedule_no
        )

        print(
            sch.schedule_title
        )

        print(
            len(
                sch.paragraphs
            )
        )

    print(
        parser.validate_schedules(
            schedules
        )
    )
