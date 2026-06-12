
from __future__ import annotations

import re

from legal_models import (
    ConstitutionDocument,
    Preamble,
    Part,
    Chapter,
    Article
)

from part_parser import PartParser
from chapter_parser import ChapterParser
from article_parser import ArticleParser
from clause_parser import ClauseParser
from proviso_parser import ProvisoParser
from explanation_parser import ExplanationParser
from schedule_parser import ScheduleParser
from reference_extractor import ReferenceExtractor


class ConstitutionParser:

    """
    Main Constitution Parser

    Orchestrates all parsers.
    """

    # =====================================================
    # INIT
    # =====================================================

    def __init__(self):

        self.part_parser = PartParser()

        self.chapter_parser = ChapterParser()

        self.article_parser = ArticleParser()

        self.clause_parser = ClauseParser()

        self.proviso_parser = ProvisoParser()

        self.explanation_parser = (
            ExplanationParser()
        )

        self.schedule_parser = (
            ScheduleParser()
        )

        self.reference_extractor = (
            ReferenceExtractor()
        )

    # =====================================================
    # OCR CLEANING
    # =====================================================

    def clean(
        self,
        text: str
    ) -> str:

        text = text.replace(
            "\r\n",
            "\n"
        )

        text = re.sub(
            r"\r",
            "\n",
            text
        )

        # remove page numbers

        text = re.sub(
            r"(?m)^\s*\d+\s*$",
            "",
            text
        )

        # remove repeated spaces

        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # remove constitution headers

        text = re.sub(
            r"THE CONSTITUTION OF INDIA",
            "",
            text,
            flags=re.I
        )

        # remove separators

        text = re.sub(
            r"_{3,}",
            "",
            text
        )

        # collapse blank lines

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()

    # =====================================================
    # PREAMBLE
    # =====================================================

    def extract_preamble(
        self,
        text: str
    ) -> Preamble:

        part_match = re.search(
            r"(?im)^PART\s+[IVXLCDM]+",
            text
        )

        if not part_match:

            return Preamble(
                document="constitution",
                text=text[:5000]
            )

        return Preamble(
            document="constitution",
            text=text[
                :part_match.start()
            ].strip()
        )

    # =====================================================
    # ARTICLE BUILD
    # =====================================================

    def build_article(
        self,
        article_data
    ) -> Article:

        article = Article(
            document="constitution",
            article_no=article_data[
                "article_no"
            ],
            article_title=article_data[
                "article_title"
            ],
            text=article_data[
                "text"
            ]
        )

        # clauses

        article.clauses.extend(
            self.clause_parser
            .parse_clauses(
                article.text
            )
        )

        # provisos

        article.provisos.extend(
            self.proviso_parser
            .parse_provisos(
                article.text
            )
        )

        # explanations

        article.explanations.extend(
            self.explanation_parser
            .parse_explanations(
                article.text
            )
        )

        # references

        article.references.extend(
            self.reference_extractor
            .deduplicate(
                self.reference_extractor
                .extract(
                    article.text
                )
            )
        )

        return article

    # =====================================================
    # PARSE PART
    # =====================================================

    def parse_part(
        self,
        part_data
    ) -> Part:

        part = Part(
            document="constitution",
            part_no=part_data[
                "part_no"
            ],
            part_title=part_data[
                "part_title"
            ]
        )

        chapters = (
            self.chapter_parser
            .extract_chapters(
                part_data["text"]
            )
        )

        # =====================================
        # PART WITH CHAPTERS
        # =====================================

        if chapters:

            for chapter_data in chapters:

                chapter = Chapter(
                    document="constitution",
                    chapter_no=
                    chapter_data[
                        "chapter_no"
                    ],
                    chapter_title=
                    chapter_data[
                        "chapter_title"
                    ]
                )

                articles = (
                    self.article_parser
                    .extract_articles(
                        chapter_data[
                            "text"
                        ]
                    )
                )

                for article_data in articles:

                    article = (
                        self.build_article(
                            article_data
                        )
                    )

                    chapter.articles.append(
                        article
                    )

                part.chapters.append(
                    chapter
                )

        # =====================================
        # PART WITHOUT CHAPTERS
        # =====================================

        else:

            articles = (
                self.article_parser
                .extract_articles(
                    part_data["text"]
                )
            )

            for article_data in articles:

                article = (
                    self.build_article(
                        article_data
                    )
                )

                part.articles.append(
                    article
                )

        return part
    
    @staticmethod
    def clean_constitution_text(text: str) -> str:

        # footnotes
        text = re.sub(
            r'(?m)^\d+\.\s+(Subs\.|Ins\.|Omitted|Added|Inserted).*?$',
            '',
            text
        )

        # page separators
        text = re.sub(
            r'_{5,}',
            '',
            text
        )

        # page numbers
        text = re.sub(
            r'(?m)^\d+\s*$',
            '',
            text
        )

        # amendment markers
        text = re.sub(
            r'\d+\[',
            '',
            text
        )

        return text

    @staticmethod
    def remove_footnotes(text: str) -> str:

        text = re.sub(
            r"(?im)^\s*\d+\s+(Subs\.|Ins\.|Omitted|Added|Inserted).*?$",
            "",
            text
        )

        text = re.sub(
            r"(?im)^\s*\d+\s+Vide.*?$",
            "",
            text
        )

        text = re.sub(
            r"(?im)^\s*\d+\s+The words.*?$",
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
    # MAIN PARSE
    # =====================================================

    def parse(
        self,
        raw_text: str
    ) -> ConstitutionDocument:

        raw_text = self.clean(
            raw_text
        )
        raw_text = self.clean_constitution_text(raw_text)
        raw_text = self.remove_footnotes(raw_text)

        document = (
            ConstitutionDocument(
                document=
                "constitution"
            )
        )

        # preamble

        document.preamble = (
            self.extract_preamble(
                raw_text
            )
        )

        # parts

        parts = (
            self.part_parser
            .extract_parts(
                raw_text
            )
        )

        for part_data in parts:

            document.parts.append(
                self.parse_part(
                    part_data
                )
            )

        # schedules

        schedules = (
            self.schedule_parser
            .extract_schedules(
                raw_text
            )
        )

        document.schedules.extend(
            schedules
        )

        return document

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate(
        self,
        document:
        ConstitutionDocument
    ):

        errors = []

        if not document.parts:

            errors.append(
                "No Parts Found"
            )

        article_count = 0

        for part in document.parts:

            article_count += len(
                part.articles
            )

            for chapter in part.chapters:

                article_count += len(
                    chapter.articles
                )

        if article_count == 0:

            errors.append(
                "No Articles Found"
            )

        return errors




def print_stats(constitution):

    total_parts = len(constitution.parts)

    total_chapters = 0
    total_articles = 0
    total_clauses = 0
    total_subclauses = 0
    total_romans = 0
    total_provisos = 0
    total_explanations = 0
    total_references = 0

    for part in constitution.parts:

        total_articles += len(part.articles)

        for article in part.articles:

            total_provisos += len(article.provisos)
            total_explanations += len(article.explanations)
            total_references += len(article.references)

            total_clauses += len(article.clauses)

            for clause in article.clauses:

                total_subclauses += len(
                    clause.sub_clauses
                )

                for sub in clause.sub_clauses:

                    total_romans += len(
                        sub.roman_clauses
                    )

        total_chapters += len(
            part.chapters
        )

        for chapter in part.chapters:

            total_articles += len(
                chapter.articles
            )

            for article in chapter.articles:

                total_provisos += len(
                    article.provisos
                )

                total_explanations += len(
                    article.explanations
                )

                total_references += len(
                    article.references
                )

                total_clauses += len(
                    article.clauses
                )

                for clause in article.clauses:

                    total_subclauses += len(
                        clause.sub_clauses
                    )

                    for sub in clause.sub_clauses:

                        total_romans += len(
                            sub.roman_clauses
                        )

    print("\n========== PARSER STATS ==========\n")

    print("Parts:", total_parts)
    print("Chapters:", total_chapters)
    print("Articles:", total_articles)
    print("Clauses:", total_clauses)
    print("SubClauses:", total_subclauses)
    print("RomanClauses:", total_romans)
    print("Provisos:", total_provisos)
    print("Explanations:", total_explanations)
    print("References:", total_references)
    print("Schedules:", len(constitution.schedules))

    print("\n==================================\n")

# =========================================================
# EXAMPLE
# =========================================================

if __name__ == "__main__":

    with open(
        "../../pdfs/constitution.txt",
        "r",
        encoding="utf8"
    ) as f:

        text = f.read()

    parser = ConstitutionParser()

    constitution = parser.parse(
        text
    )

    print_stats(constitution)