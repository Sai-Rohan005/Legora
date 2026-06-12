# from __future__ import annotations

# import re
# from dataclasses import dataclass, field, asdict
# from typing import List
# from models.legal_models import Article, Part, Explanation, Proviso, RomanClause, SubClause, Clause

# # ==========================================================
# # DATA MODELS
# # ==========================================================

# @dataclass
# class Reference:
#     article_no: str


# # @dataclass
# # class Explanation:
# #     text: str


# # @dataclass
# # class Proviso:
# #     text: str


# # @dataclass
# # class RomanClause:
# #     roman_no: str
# #     text: str


# # @dataclass
# # class SubClause:
# #     sub_clause_no: str
# #     text: str
# #     roman_clauses: List[RomanClause] = field(default_factory=list)


# # @dataclass
# # class Clause:
# #     clause_no: str
# #     text: str
# #     sub_clauses: List[SubClause] = field(default_factory=list)


# # @dataclass
# # class Article:
# #     article_no: str
# #     article_title: str
# #     text: str

# #     clauses: List[Clause] = field(default_factory=list)
# #     provisos: List[Proviso] = field(default_factory=list)
# #     explanations: List[Explanation] = field(default_factory=list)
# #     references: List[Reference] = field(default_factory=list)


# # @dataclass
# # class Part:
# #     part_no: str
# #     part_title: str
# #     articles: List[Article] = field(default_factory=list)


# # ==========================================================
# # PARSER
# # ==========================================================

# class ConstitutionParser:

#     PART_RE = re.compile(
#         r"PART\s+([IVXLC]+)\s*\n+([^\n]+)",
#         re.IGNORECASE
#     )

#     ARTICLE_RE = re.compile(
#         r"(?m)^(\d{1,3}[A-Z]?)\.\s*(.+)$"
#     )

#     CLAUSE_RE = re.compile(
#         r"(?m)^\((\d+[A-Za-z]?)\)\s*(.*)"
#     )

#     SUBCLAUSE_RE = re.compile(
#         r"(?m)^\(([a-hj-z])\)\s*(.*)"
#     )

#     ROMAN_RE = re.compile(
#         r"(?m)^\((i|ii|iii|iv|v|vi|vii|viii|ix|x)\)\s*(.*)"
#     )

#     PROVISO_RE = re.compile(
#         r"(?is)"
#         r"(Provided(?:\s+further)?(?:\s+also)?\s+that.*?)(?="
#         r"Provided(?:\s+further)?(?:\s+also)?\s+that"
#         r"|Explanation"
#         r"|$)"
#     )

#     EXPLANATION_RE = re.compile(
#         r"(?is)"
#         r"(Explanation.*?)(?="
#         r"Provided"
#         r"|$)"
#     )

#     REFERENCE_RE = re.compile(
#         r"article[s]?\s+(\d+[A-Z]?)",
#         re.IGNORECASE
#     )

#     # ======================================================
#     # OCR CLEANING
#     # ======================================================

#     def clean(self, text: str):

#         text = text.replace("\r\n", "\n")

#         # remove page numbers
#         text = re.sub(
#             r"(?m)^\s*\d+\s*$",
#             "",
#             text
#         )

#         # remove constitution headers
#         text = re.sub(
#             r"THE CONSTITUTION OF INDIA",
#             "",
#             text,
#             flags=re.IGNORECASE
#         )

#         # remove separators
#         text = re.sub(
#             r"_{5,}",
#             "",
#             text
#         )

#         # remove amendment notes
#         text = re.sub(
#             r"(?m)^\d+\.\s+(Subs\.|Ins\.|Added|Omitted).*?$",
#             "",
#             text
#         )

#         text = re.sub(
#             r"\n{3,}",
#             "\n\n",
#             text
#         )

#         return text.strip()

#     # ======================================================
#     # PARTS
#     # ======================================================

#     def extract_parts(self, text):

#         matches = list(self.PART_RE.finditer(text))

#         results = []

#         for i, m in enumerate(matches):

#             start = m.start()

#             end = (
#                 matches[i + 1].start()
#                 if i + 1 < len(matches)
#                 else len(text)
#             )

#             results.append({
#                 "part_no": m.group(1).strip(),
#                 "part_title": m.group(2).strip(),
#                 "text": text[start:end]
#             })

#         return results

#     # ======================================================
#     # ARTICLES
#     # ======================================================

#     def extract_articles(self, text):

#         matches = list(self.ARTICLE_RE.finditer(text))

#         results = []

#         for i, m in enumerate(matches):

#             start = m.start()

#             end = (
#                 matches[i + 1].start()
#                 if i + 1 < len(matches)
#                 else len(text)
#             )

#             results.append({
#                 "article_no": m.group(1),
#                 "article_title": m.group(2).strip(),
#                 "text": text[start:end].strip()
#             })

#         return results

#     # ======================================================
#     # CLAUSES
#     # ======================================================

#     def extract_clauses(self, text):

#         matches = list(self.CLAUSE_RE.finditer(text))

#         results = []

#         for i, m in enumerate(matches):

#             start = m.start()

#             end = (
#                 matches[i + 1].start()
#                 if i + 1 < len(matches)
#                 else len(text)
#             )

#             results.append({
#                 "clause_no": m.group(1),
#                 "text": text[start:end].strip()
#             })

#         return results

#     # ======================================================
#     # SUB CLAUSES
#     # ======================================================

#     def extract_subclauses(self, text):

#         matches = list(self.SUBCLAUSE_RE.finditer(text))

#         results = []

#         for i, m in enumerate(matches):

#             start = m.start()

#             end = (
#                 matches[i + 1].start()
#                 if i + 1 < len(matches)
#                 else len(text)
#             )

#             results.append({
#                 "sub_clause_no": m.group(1),
#                 "text": text[start:end].strip()
#             })

#         return results

#     # ======================================================
#     # ROMAN CLAUSES
#     # ======================================================

#     def extract_roman_clauses(self, text):

#         matches = list(self.ROMAN_RE.finditer(text))

#         results = []

#         for i, m in enumerate(matches):

#             start = m.start()

#             end = (
#                 matches[i + 1].start()
#                 if i + 1 < len(matches)
#                 else len(text)
#             )

#             results.append({
#                 "roman_no": m.group(1),
#                 "text": text[start:end].strip()
#             })

#         return results

#     # ======================================================
#     # PROVISOS
#     # ======================================================

#     def extract_provisos(self, text):

#         return [
#             Proviso(text=m.strip())
#             for m in self.PROVISO_RE.findall(text)
#         ]

#     # ======================================================
#     # EXPLANATIONS
#     # ======================================================

#     def extract_explanations(self, text):

#         return [
#             Explanation(text=m.strip())
#             for m in self.EXPLANATION_RE.findall(text)
#         ]

#     # ======================================================
#     # REFERENCES
#     # ======================================================

#     def extract_references(self, text):

#         refs = sorted(
#             set(
#                 self.REFERENCE_RE.findall(text)
#             )
#         )

#         return [
#             Reference(article_no=r)
#             for r in refs
#         ]

#     # ======================================================
#     # MAIN PARSER
#     # ======================================================

#     def parse(self, raw_text):

#         raw_text = self.clean(raw_text)

#         parsed_parts = []

#         for p in self.extract_parts(raw_text):

#             part = Part(
#                 document="constitution",
#                 part_no=p["part_no"],
#                 part_title=p["part_title"]
#             )

#             for a in self.extract_articles(p["text"]):

#                 article = Article(
#                     document="constitution",
#                     article_no=a["article_no"],
#                     article_title=a["article_title"],
#                     text=a["text"]
#                 )

#                 article.provisos = self.extract_provisos(
#                     article.text
#                 )

#                 article.explanations = self.extract_explanations(
#                     article.text
#                 )

#                 article.references = self.extract_references(
#                     article.text
#                 )

#                 for c in self.extract_clauses(article.text):

#                     clause = Clause(
#                         document="constitution",
#                         clause_no=c["clause_no"],
#                         text=c["text"]
#                     )

#                     for s in self.extract_subclauses(
#                         clause.text
#                     ):

#                         sub = SubClause(
#                             document="constitution",
#                             sub_clause_no=s["sub_clause_no"],
#                             text=s["text"]
#                         )

#                         for r in self.extract_roman_clauses(
#                             sub.text
#                         ):

#                             sub.roman_clauses.append(
#                                 RomanClause(
#                                     document="constitution",
#                                     roman_no=r["roman_no"],
#                                     text=r["text"]
#                                 )
#                             )

#                         clause.sub_clauses.append(sub)

#                     article.clauses.append(clause)

#                 part.articles.append(article)

#             parsed_parts.append(part)

#         return parsed_parts


# # ==========================================================
# # EXAMPLE
# # ==========================================================

# if __name__ == "__main__":

#     with open("text_extracted_ocr_output.txt", "r", encoding="utf8") as f:
#         text = f.read()

#     parser = ConstitutionParser()

#     result = parser.parse(text)

#     print(asdict(result[0]))













from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ==========================================================
# BASE NODE
# ==========================================================

@dataclass
class LegalNode:
    """
    Base node used by all legal entities.
    """

    document: str

    id: Optional[str] = None

    parent_id: Optional[str] = None

    source_text: Optional[str] = None

    start_offset: Optional[int] = None

    end_offset: Optional[int] = None


# ==========================================================
# REFERENCES
# ==========================================================

@dataclass
class Reference:

    reference_type: str

    reference_value: str

    text: str = ""


# ==========================================================
# PROVISO
# ==========================================================

@dataclass
class Proviso(LegalNode):

    text: str = ""


# ==========================================================
# EXPLANATION
# ==========================================================

@dataclass
class Explanation(LegalNode):

    explanation_no: str = ""

    text: str = ""


# ==========================================================
# ILLUSTRATION
# ==========================================================

@dataclass
class Illustration(LegalNode):

    illustration_no: str = ""

    text: str = ""


# ==========================================================
# ROMAN CLAUSE
# ==========================================================

@dataclass
class RomanClause(LegalNode):

    roman_no: str = ""

    text: str = ""


# ==========================================================
# SUB CLAUSE
# ==========================================================

@dataclass
class SubClause(LegalNode):

    sub_clause_no: str = ""

    text: str = ""

    roman_clauses: List[RomanClause] = field(
        default_factory=list
    )


# ==========================================================
# CLAUSE
# ==========================================================

@dataclass
class Clause(LegalNode):

    clause_no: str = ""

    text: str = ""

    sub_clauses: List[SubClause] = field(
        default_factory=list
    )


# ==========================================================
# ARTICLE
# ==========================================================

@dataclass
class Article(LegalNode):

    article_no: str = ""

    article_title: str = ""

    text: str = ""

    clauses: List[Clause] = field(
        default_factory=list
    )

    provisos: List[Proviso] = field(
        default_factory=list
    )

    explanations: List[Explanation] = field(
        default_factory=list
    )

    illustrations: List[Illustration] = field(
        default_factory=list
    )

    references: List[Reference] = field(
        default_factory=list
    )


# ==========================================================
# CHAPTER
# ==========================================================

@dataclass
class Chapter(LegalNode):

    chapter_no: str = ""

    chapter_title: str = ""

    articles: List[Article] = field(
        default_factory=list
    )


# ==========================================================
# PART
# ==========================================================

@dataclass
class Part(LegalNode):

    part_no: str = ""

    part_title: str = ""

    chapters: List[Chapter] = field(
        default_factory=list
    )

    articles: List[Article] = field(
        default_factory=list
    )


# ==========================================================
# SCHEDULE PARAGRAPH
# ==========================================================

@dataclass
class ScheduleParagraph(LegalNode):

    paragraph_no: str = ""

    text: str = ""


# ==========================================================
# SCHEDULE
# ==========================================================

@dataclass
class Schedule(LegalNode):

    schedule_no: str = ""

    schedule_title: str = ""

    text: str = ""

    paragraphs: List[ScheduleParagraph] = field(
        default_factory=list
    )

    references: List[Reference] = field(
        default_factory=list
    )


# ==========================================================
# PREAMBLE
# ==========================================================

@dataclass
class Preamble(LegalNode):

    text: str = ""


# ==========================================================
# CONSTITUTION DOCUMENT
# ==========================================================

@dataclass
class ConstitutionDocument(LegalNode):

    title: str = "Constitution of India"

    preamble: Optional[Preamble] = None

    parts: List[Part] = field(
        default_factory=list
    )

    schedules: List[Schedule] = field(
        default_factory=list
    )


# ==========================================================
# UTILITIES
# ==========================================================

def build_id(
    prefix: str,
    value: str
) -> str:

    value = value.replace(" ", "_")

    return f"{prefix}:{value}"


def assign_ids(
    constitution: ConstitutionDocument
):

    constitution.id = "constitution"

    for part in constitution.parts:

        part.id = build_id(
            "part",
            part.part_no
        )

        part.parent_id = constitution.id

        for chapter in part.chapters:

            chapter.id = build_id(
                "chapter",
                chapter.chapter_no
            )

            chapter.parent_id = part.id

            for article in chapter.articles:

                article.id = build_id(
                    "article",
                    article.article_no
                )

                article.parent_id = chapter.id

        for article in part.articles:

            article.id = build_id(
                "article",
                article.article_no
            )

            article.parent_id = part.id

    for schedule in constitution.schedules:

        schedule.id = build_id(
            "schedule",
            schedule.schedule_no
        )

        schedule.parent_id = constitution.id



from __future__ import annotations

import re
from typing import List, Dict


class PartParser:
    """
    Constitution Part Parser

    Extracts:

        PART I
        THE UNION AND ITS TERRITORY

        PART II
        CITIZENSHIP

    and returns the entire text
    belonging to each Part.
    """

    # =====================================================
    # PART PATTERN
    # =====================================================

    PART_RE = re.compile(
        r"(?im)^PART\s+([IVXLCDM]+)\s*$"
    )

    # =====================================================
    # CLEAN TITLE
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
    # EXTRACT TITLE
    # =====================================================

    def extract_part_title(
        self,
        text: str,
        part_start: int
    ) -> str:

        """
        Usually title is within next 5 lines
        after PART I
        """

        chunk = text[part_start:part_start + 1000]

        lines = [
            x.strip()
            for x in chunk.split("\n")
            if x.strip()
        ]

        if len(lines) < 2:
            return ""

        title_lines = []

        for line in lines[1:6]:

            # stop if article starts

            if re.match(
                r"^\d+[A-Z]{0,3}\.",
                line
            ):
                break

            # stop if chapter starts

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
    # EXTRACT PARTS
    # =====================================================

    def extract_parts(
        self,
        text: str
    ) -> List[Dict]:

        matches = list(
            self.PART_RE.finditer(text)
        )

        if not matches:
            return []

        parts = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            part_no = match.group(1)

            part_title = self.extract_part_title(
                text,
                start
            )

            part_text = text[start:end].strip()

            parts.append(
                {
                    "part_no": part_no,
                    "part_title": part_title,
                    "text": part_text,
                    "start": start,
                    "end": end
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

        if not parts:

            errors.append(
                "No Parts Found"
            )

            return errors

        seen = set()

        for part in parts:

            part_no = part["part_no"]

            if part_no in seen:

                errors.append(
                    f"Duplicate Part {part_no}"
                )

            seen.add(part_no)

            if not part["part_title"]:

                errors.append(
                    f"Missing title for Part {part_no}"
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

    parser = PartParser()

    parts = parser.extract_parts(text)

    print(
        f"Parts Found: {len(parts)}"
    )

    for part in parts[:5]:

        print(
            part["part_no"],
            part["part_title"]
        )

    print(
        parser.validate_parts(parts)
    )


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
        r"(?im)^CHAPTER\s+([IVXLCDM]+[A-Z]?)\s*$"
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


from __future__ import annotations

import re
from typing import List, Dict


class ArticleParser:
    """
    Constitution Article Parser

    Supports:

        1.
        21A.
        239AA.
        243ZG.

    Returns:

        article_no
        article_title
        article_text
        start
        end
    """

    # =====================================================
    # ARTICLE HEADER
    # =====================================================

    ARTICLE_RE = re.compile(
        r"(?m)^(\d{1,3}[A-Z]{0,3})\.\s*(.*?)\s*$"
    )

    # =====================================================
    # ARTICLE NUMBER VALIDATOR
    # =====================================================

    ARTICLE_NUMBER_RE = re.compile(
        r"^\d{1,3}[A-Z]{0,3}$"
    )

    # =====================================================
    # CLEAN TITLE
    # =====================================================

    @staticmethod
    def clean_title(title: str) -> str:

        title = title.strip()

        title = re.sub(
            r"\s+",
            " ",
            title
        )

        title = title.rstrip(
            "."
        )

        title = title.rstrip(
            "—"
        )

        title = title.strip()

        return title

    # =====================================================
    # RECOVER MULTI LINE TITLE
    # =====================================================

    def recover_title(
        self,
        article_text: str,
        current_title: str
    ) -> str:

        if current_title:
            return self.clean_title(
                current_title
            )

        lines = [
            line.strip()
            for line in article_text.split(
                "\n"
            )
            if line.strip()
        ]

        if len(lines) < 2:
            return ""

        candidate = lines[1]

        if len(candidate) > 150:
            return ""

        return self.clean_title(
            candidate
        )

    # =====================================================
    # EXTRACT ARTICLES
    # =====================================================

    def extract_articles(
        self,
        text: str
    ) -> List[Dict]:

        matches = list(
            self.ARTICLE_RE.finditer(
                text
            )
        )

        if not matches:
            return []

        articles = []

        for i, match in enumerate(
            matches
        ):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            article_no = (
                match.group(1)
                .strip()
            )

            article_title = (
                match.group(2)
                .strip()
            )

            article_text = (
                text[start:end]
                .strip()
            )

            article_title = (
                self.recover_title(
                    article_text,
                    article_title
                )
            )

            articles.append(
                {
                    "article_no":
                        article_no,

                    "article_title":
                        article_title,

                    "text":
                        article_text,

                    "start":
                        start,

                    "end":
                        end
                }
            )

        return articles

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_articles(
        self,
        articles: List[Dict]
    ) -> List[str]:

        errors = []

        seen = set()

        for article in articles:

            article_no = (
                article["article_no"]
            )

            if article_no in seen:

                errors.append(
                    f"Duplicate "
                    f"Article "
                    f"{article_no}"
                )

            seen.add(
                article_no
            )

            if not self.ARTICLE_NUMBER_RE.match(
                article_no
            ):

                errors.append(
                    f"Invalid Article "
                    f"Number "
                    f"{article_no}"
                )

            if not article[
                "article_title"
            ]:

                errors.append(
                    f"Missing title "
                    f"for Article "
                    f"{article_no}"
                )

        return errors

    # =====================================================
    # FIND ARTICLE
    # =====================================================

    def get_article(
        self,
        articles: List[Dict],
        article_no: str
    ):

        for article in articles:

            if (
                article["article_no"]
                == article_no
            ):
                return article

        return None


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

    parser = ArticleParser()

    articles = (
        parser.extract_articles(
            text
        )
    )

    print(
        f"Articles Found: "
        f"{len(articles)}"
    )

    for article in articles[:10]:

        print(
            article["article_no"],
            article["article_title"]
        )

    errors = (
        parser.validate_articles(
            articles
        )
    )

    print(
        f"Errors: {len(errors)}"
    )

    for e in errors[:20]:
        print(e)



from __future__ import annotations

import re
from typing import List

from models.legal_models import (
    Clause,
    SubClause,
    RomanClause
)


class ClauseParser:

    """
    Recursive Clause Parser

    Handles:

        (1)
        (2)
        (2A)

    Sub Clauses:

        (a)
        (b)

    Roman Clauses:

        (i)
        (ii)
        (iii)
        (xiv)

    """

    # =====================================================
    # REGEX
    # =====================================================

    CLAUSE_RE = re.compile(
        r"(?m)^\((\d+[A-Z]?)\)\s"
    )

    SUBCLAUSE_RE = re.compile(
        r"(?m)^\(([a-z])\)\s"
    )

    ROMAN_RE = re.compile(
        r"(?m)^\(([ivxlcdm]+)\)\s",
        re.IGNORECASE
    )

    # =====================================================
    # SPLIT BY MARKER
    # =====================================================

    def split_sections(
        self,
        text: str,
        pattern: re.Pattern
    ):

        matches = list(
            pattern.finditer(text)
        )

        if not matches:
            return []

        sections = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            sections.append(
                (
                    match.group(1),
                    text[start:end].strip()
                )
            )

        return sections

    # =====================================================
    # ROMAN CLAUSES
    # =====================================================

    def parse_roman_clauses(
        self,
        text: str
    ) -> List[RomanClause]:

        romans = []

        for roman_no, roman_text in self.split_sections(
            text,
            self.ROMAN_RE
        ):

            romans.append(
                RomanClause(
                    document="constitution",
                    roman_no=roman_no,
                    text=roman_text
                )
            )

        return romans

    # =====================================================
    # SUB CLAUSES
    # =====================================================

    def parse_subclauses(
        self,
        text: str
    ) -> List[SubClause]:

        subclauses = []

        for sub_no, sub_text in self.split_sections(
            text,
            self.SUBCLAUSE_RE
        ):

            sub = SubClause(
                document="constitution",
                sub_clause_no=sub_no,
                text=sub_text
            )

            sub.roman_clauses.extend(
                self.parse_roman_clauses(
                    sub_text
                )
            )

            subclauses.append(sub)

        return subclauses

    # =====================================================
    # CLAUSES
    # =====================================================

    def parse_clauses(
        self,
        article_text: str
    ) -> List[Clause]:

        clauses = []

        clause_sections = self.split_sections(
            article_text,
            self.CLAUSE_RE
        )

        if not clause_sections:
            return clauses

        for clause_no, clause_text in clause_sections:

            clause = Clause(
                document="constitution",
                clause_no=clause_no,
                text=clause_text
            )

            clause.sub_clauses.extend(
                self.parse_subclauses(
                    clause_text
                )
            )

            clauses.append(clause)

        return clauses

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_clauses(
        self,
        clauses: List[Clause]
    ) -> List[str]:

        errors = []

        seen = set()

        for clause in clauses:

            if clause.clause_no in seen:

                errors.append(
                    f"Duplicate Clause "
                    f"{clause.clause_no}"
                )

            seen.add(
                clause.clause_no
            )

            sub_seen = set()

            for sub in clause.sub_clauses:

                if sub.sub_clause_no in sub_seen:

                    errors.append(
                        f"Duplicate SubClause "
                        f"{sub.sub_clause_no} "
                        f"in Clause "
                        f"{clause.clause_no}"
                    )

                sub_seen.add(
                    sub.sub_clause_no
                )

                roman_seen = set()

                for roman in sub.roman_clauses:

                    if roman.roman_no in roman_seen:

                        errors.append(
                            f"Duplicate Roman "
                            f"{roman.roman_no}"
                        )

                    roman_seen.add(
                        roman.roman_no
                    )

        return errors


# =========================================================
# EXAMPLE
# =========================================================

if __name__ == "__main__":

    sample = '''
(1) The State may make laws.

(a) for education

(i) primary education

(ii) secondary education

(b) for health

(2) Parliament may legislate.
'''

    parser = ClauseParser()

    clauses = parser.parse_clauses(
        sample
    )

    print(
        f"Clauses: "
        f"{len(clauses)}"
    )

    for clause in clauses:

        print(
            clause.clause_no,
            len(clause.sub_clauses)
        )

    print(
        parser.validate_clauses(
            clauses
        )
    )
