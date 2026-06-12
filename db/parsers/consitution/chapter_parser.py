
from __future__ import annotations

import re
from typing import List, Dict


class ChapterParser:
    """
    Constitution Chapter Parser

    Extracts:

        CHAPTER I
        THE EXECUTIVE

        CHAPTER II
        PARLIAMENT

    and returns text belonging
    to each chapter.
    """

    # =====================================================
    # CHAPTER REGEX
    # =====================================================

    CHAPTER_RE = re.compile(
        r"""
        ^
        CHAPTER
        \s+
        ([IVXLCDM]+)
        \.?          # optional OCR period
        [—\-–]
        \s*
        (.+?)
        $
        """,
        re.MULTILINE
        | re.IGNORECASE
        | re.VERBOSE
    )

    # =====================================================
    # TITLE CLEANER
    # =====================================================

    @staticmethod
    def clean_title(title: str) -> str:

        title = title.strip()

        title = re.sub(
            r"\s+",
            " ",
            title
        )

        return title

    # =====================================================
    # EXTRACT CHAPTER TITLE
    # =====================================================

    def extract_chapter_title(
        self,
        text: str,
        chapter_start: int
    ) -> str:

        chunk = text[
            chapter_start:
            chapter_start + 1000
        ]

        lines = [
            line.strip()
            for line in chunk.split("\n")
            if line.strip()
        ]

        if len(lines) < 2:
            return ""

        title_lines = []

        for line in lines[1:6]:

            # stop at article

            if re.match(
                r"^\d+[A-Z]{0,3}\.",
                line
            ):
                break

            # stop at next chapter

            if re.match(
                r"^CHAPTER\s+",
                line,
                re.I
            ):
                break

            title_lines.append(line)

        return self.clean_title(
            " ".join(title_lines)
        )

    # =====================================================
    # EXTRACT CHAPTERS
    # =====================================================

    def extract_chapters(
        self,
        text: str
    ) -> List[Dict]:

        matches = list(
            self.CHAPTER_RE.finditer(text)
        )

        if not matches:
            return []

        chapters = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            chapter_no = match.group(1)

            chapter_title = (
                self.extract_chapter_title(
                    text,
                    start
                )
            )

            chapter_text = (
                text[start:end]
                .strip()
            )

            chapters.append(
                {
                    "chapter_no":
                        chapter_no,

                    "chapter_title":
                        chapter_title,

                    "text":
                        chapter_text,

                    "start":
                        start,

                    "end":
                        end
                }
            )

        return chapters

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_chapters(
        self,
        chapters: List[Dict]
    ) -> List[str]:

        errors = []

        seen = set()

        for chapter in chapters:

            chapter_no = (
                chapter["chapter_no"]
            )

            if chapter_no in seen:

                errors.append(
                    f"Duplicate Chapter "
                    f"{chapter_no}"
                )

            seen.add(chapter_no)

            if not chapter[
                "chapter_title"
            ]:

                errors.append(
                    f"Missing title for "
                    f"Chapter {chapter_no}"
                )

        return errors


# =========================================================
# EXAMPLE
# =========================================================

if __name__ == "__main__":

    with open(
        "constitution.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()

    parser = ChapterParser()

    chapters = (
        parser.extract_chapters(
            text
        )
    )

    print(
        f"Found "
        f"{len(chapters)} "
        f"chapters"
    )

    for chapter in chapters[:10]:

        print(
            chapter["chapter_no"],
            chapter["chapter_title"]
        )

    print(
        parser.validate_chapters(
            chapters
        )
    )
