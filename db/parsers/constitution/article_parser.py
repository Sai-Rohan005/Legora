
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
        r"""
        ^
        (\d{1,3}[A-Z]{0,3})
        \.

        \s+

        ([A-Z][^\n]{10,300})

        $
        """,
        re.MULTILINE | re.VERBOSE
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
    # EXTRACT ARTICLES
    # =====================================================

    def extract_articles(
        self,
        text: str
    ) -> List[Dict]:
        text = self.clean_constitution_text(text)
        text=self.remove_footnotes(text)
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
            title = match.group(2).strip()

            if title.startswith(
                (
                    "Subs.",
                    "Ins.",
                    "Omitted",
                    "Added",
                    "Inserted"
                )
            ):
                continue

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
        "../../pdfs/constitution.txt",
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
