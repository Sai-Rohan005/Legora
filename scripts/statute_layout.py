"""Keep printed footnotes and schedules from becoming false provision identities."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)
SCHEDULE_HEADING = re.compile(
    r"(?im)^\s*(?:\d+\[)?(?:THE\s+)?(?:(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH|ELEVENTH|TWELFTH)\s+)?SCHEDULE\s*$"
)


def prepare_source(name: str, text: str) -> str:
    """Normalize known printed boundaries without editing the user's source files."""
    if name in {"bnss", "bsa"}:
        schedule = SCHEDULE_HEADING.search(text)
        if schedule:
            logger.warning("%s: schedules excluded from section parsing; separate schedule ingestion is unsupported", name)
            return text[:schedule.start()]
    if name != "constitution":
        return text
    lines = text.splitlines()
    output: list[str] = []
    skipping = False
    for index, line in enumerate(lines):
        if re.fullmatch(r"\s*_{5,}\s*", line):
            following = next((value.strip() for value in lines[index + 1:] if value.strip()), "")
            # An article heading with its operative dash is not an editorial footer.
            skipping = bool(re.match(r"\d+\.\s+", following) and not re.search(r"[.—]—|––", following))
            continue
        if skipping and (
            re.fullmatch(r"\s*(?:\d+|THE CONSTITUTION OF INDIA|PART [IVXLCDMA-Z]+)\s*", line)
            or SCHEDULE_HEADING.fullmatch(line)
            or re.fullmatch(r"APPENDIX\s+[IVXLCDM]+", line.strip())
        ):
            skipping = False
        if not skipping:
            output.append(line)
    return "\n".join(output)
