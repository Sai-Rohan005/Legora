
from __future__ import annotations

import re
from typing import List, Dict

from db.parsers.bsa.legal_models import Chapter


class ChapterParser:
    """
    Bharatiya Nyaya Sanhita Chapter Parser

    Extracts:

        CHAPTER I
        PRELIMINARY

        CHAPTER II
        OF PUNISHMENTS

    Returns:

        chapter_no
        chapter_title
        text
        start
        end
    """

    # =====================================================
    # CHAPTER HEADER
    # =====================================================

    # CHAPTER_RE = re.compile(
    #     r"(?m)^CHAPTER\s+([IVXLCDM]+)\s*$"
    # )

    CHAPTER_RE = re.compile(
        r"(?im)^(?:\d+\.\s*)?CHAPTER\s+([IVXLCDM]+)\s*$"
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
            "-— "
        )

        return title

    # =====================================================
    # EXTRACT CHAPTER TITLE
    # =====================================================

    def extract_title(
        self,
        text: str,
        start: int
    ) -> str:

        chunk = text[
            start:start + 1000
        ]

        lines = [
            x.strip()
            for x in chunk.split("\n")
            if x.strip()
        ]

        if len(lines) < 2:
            return ""

        for line in lines[1:10]:

            # Stop if section starts

            if re.match(
                r"^\d+\.",
                line
            ):
                break

            # Stop if another chapter

            if re.match(
                r"^CHAPTER\s+",
                line,
                re.I
            ):
                break

            # Ignore page numbers

            if re.match(
                r"^\d+$",
                line
            ):
                continue

            if len(line) < 200:

                return self.clean_title(
                    line
                )

        return ""

    # =====================================================
    # EXTRACT CHAPTERS
    # =====================================================

    def extract_chapters(
        self,
        text: str
    ) -> List[Dict]:

        matches = list(
            self.CHAPTER_RE.finditer(
                text
            )
        )

        if not matches:
            return []

        chapters = []

        for i, match in enumerate(
            matches
        ):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            chapter_no = (
                match.group(1)
                .strip()
            )

            chapter_title = (
                self.extract_title(
                    text,
                    start
                )
            )

            chapter_text = (
                text[start:end]
                .strip()
            )

            chapters.append(
                Chapter(
                    document="bsa",
                    chapter_no=chapter_no,
                    title=chapter_title,
                    text=chapter_text
                )
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

            seen.add(
                chapter_no
            )

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
        "../../pdfs/bsa.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()

    

    parser = ChapterParser()

    chapters = parser.extract_chapters(text)

    for chapter_dict in chapters[:2]:
        print("\n" + "="*100)
        print("CHAPTER:", chapter_dict["chapter_no"])
        print(chapter_dict["text"][:3000])






    # chapters = (
    #     parser.extract_chapters(
    #         text
    #     )
    # )

    # print(
    #     f"Chapters Found: "
    #     f"{len(chapters)}\n"
    # )

    # for chapter in chapters:

    #     print(
    #         f"{chapter['chapter_no']} "
    #         f"-> "
    #         f"{chapter['chapter_title']}"
    #     )

    # print()

    # errors = (
    #     parser.validate_chapters(
    #         chapters
    #     )
    # )

    # print(
    #     f"Errors: "
    #     f"{len(errors)}"
    # )

    # for e in errors:
    #     print(e)
