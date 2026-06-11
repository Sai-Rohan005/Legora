from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import List
from models.legal_models import Article, Part, Explanation, Proviso, RomanClause, SubClause, Clause

# ==========================================================
# DATA MODELS
# ==========================================================

@dataclass
class Reference:
    article_no: str


# @dataclass
# class Explanation:
#     text: str


# @dataclass
# class Proviso:
#     text: str


# @dataclass
# class RomanClause:
#     roman_no: str
#     text: str


# @dataclass
# class SubClause:
#     sub_clause_no: str
#     text: str
#     roman_clauses: List[RomanClause] = field(default_factory=list)


# @dataclass
# class Clause:
#     clause_no: str
#     text: str
#     sub_clauses: List[SubClause] = field(default_factory=list)


# @dataclass
# class Article:
#     article_no: str
#     article_title: str
#     text: str

#     clauses: List[Clause] = field(default_factory=list)
#     provisos: List[Proviso] = field(default_factory=list)
#     explanations: List[Explanation] = field(default_factory=list)
#     references: List[Reference] = field(default_factory=list)


# @dataclass
# class Part:
#     part_no: str
#     part_title: str
#     articles: List[Article] = field(default_factory=list)


# ==========================================================
# PARSER
# ==========================================================

class ConstitutionParser:

    PART_RE = re.compile(
        r"PART\s+([IVXLC]+)\s*\n+([^\n]+)",
        re.IGNORECASE
    )

    ARTICLE_RE = re.compile(
        r"(?m)^(\d{1,3}[A-Z]?)\.\s*(.+)$"
    )

    CLAUSE_RE = re.compile(
        r"(?m)^\((\d+[A-Za-z]?)\)\s*(.*)"
    )

    SUBCLAUSE_RE = re.compile(
        r"(?m)^\(([a-hj-z])\)\s*(.*)"
    )

    ROMAN_RE = re.compile(
        r"(?m)^\((i|ii|iii|iv|v|vi|vii|viii|ix|x)\)\s*(.*)"
    )

    PROVISO_RE = re.compile(
        r"(?is)"
        r"(Provided(?:\s+further)?(?:\s+also)?\s+that.*?)(?="
        r"Provided(?:\s+further)?(?:\s+also)?\s+that"
        r"|Explanation"
        r"|$)"
    )

    EXPLANATION_RE = re.compile(
        r"(?is)"
        r"(Explanation.*?)(?="
        r"Provided"
        r"|$)"
    )

    REFERENCE_RE = re.compile(
        r"article[s]?\s+(\d+[A-Z]?)",
        re.IGNORECASE
    )

    # ======================================================
    # OCR CLEANING
    # ======================================================

    def clean(self, text: str):

        text = text.replace("\r\n", "\n")

        # remove page numbers
        text = re.sub(
            r"(?m)^\s*\d+\s*$",
            "",
            text
        )

        # remove constitution headers
        text = re.sub(
            r"THE CONSTITUTION OF INDIA",
            "",
            text,
            flags=re.IGNORECASE
        )

        # remove separators
        text = re.sub(
            r"_{5,}",
            "",
            text
        )

        # remove amendment notes
        text = re.sub(
            r"(?m)^\d+\.\s+(Subs\.|Ins\.|Added|Omitted).*?$",
            "",
            text
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()

    # ======================================================
    # PARTS
    # ======================================================

    def extract_parts(self, text):

        matches = list(self.PART_RE.finditer(text))

        results = []

        for i, m in enumerate(matches):

            start = m.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append({
                "part_no": m.group(1).strip(),
                "part_title": m.group(2).strip(),
                "text": text[start:end]
            })

        return results

    # ======================================================
    # ARTICLES
    # ======================================================

    def extract_articles(self, text):

        matches = list(self.ARTICLE_RE.finditer(text))

        results = []

        for i, m in enumerate(matches):

            start = m.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append({
                "article_no": m.group(1),
                "article_title": m.group(2).strip(),
                "text": text[start:end].strip()
            })

        return results

    # ======================================================
    # CLAUSES
    # ======================================================

    def extract_clauses(self, text):

        matches = list(self.CLAUSE_RE.finditer(text))

        results = []

        for i, m in enumerate(matches):

            start = m.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append({
                "clause_no": m.group(1),
                "text": text[start:end].strip()
            })

        return results

    # ======================================================
    # SUB CLAUSES
    # ======================================================

    def extract_subclauses(self, text):

        matches = list(self.SUBCLAUSE_RE.finditer(text))

        results = []

        for i, m in enumerate(matches):

            start = m.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append({
                "sub_clause_no": m.group(1),
                "text": text[start:end].strip()
            })

        return results

    # ======================================================
    # ROMAN CLAUSES
    # ======================================================

    def extract_roman_clauses(self, text):

        matches = list(self.ROMAN_RE.finditer(text))

        results = []

        for i, m in enumerate(matches):

            start = m.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append({
                "roman_no": m.group(1),
                "text": text[start:end].strip()
            })

        return results

    # ======================================================
    # PROVISOS
    # ======================================================

    def extract_provisos(self, text):

        return [
            Proviso(text=m.strip())
            for m in self.PROVISO_RE.findall(text)
        ]

    # ======================================================
    # EXPLANATIONS
    # ======================================================

    def extract_explanations(self, text):

        return [
            Explanation(text=m.strip())
            for m in self.EXPLANATION_RE.findall(text)
        ]

    # ======================================================
    # REFERENCES
    # ======================================================

    def extract_references(self, text):

        refs = sorted(
            set(
                self.REFERENCE_RE.findall(text)
            )
        )

        return [
            Reference(article_no=r)
            for r in refs
        ]

    # ======================================================
    # MAIN PARSER
    # ======================================================

    def parse(self, raw_text):

        raw_text = self.clean(raw_text)

        parsed_parts = []

        for p in self.extract_parts(raw_text):

            part = Part(
                document="constitution",
                part_no=p["part_no"],
                part_title=p["part_title"]
            )

            for a in self.extract_articles(p["text"]):

                article = Article(
                    document="constitution",
                    article_no=a["article_no"],
                    article_title=a["article_title"],
                    text=a["text"]
                )

                article.provisos = self.extract_provisos(
                    article.text
                )

                article.explanations = self.extract_explanations(
                    article.text
                )

                article.references = self.extract_references(
                    article.text
                )

                for c in self.extract_clauses(article.text):

                    clause = Clause(
                        document="constitution",
                        clause_no=c["clause_no"],
                        text=c["text"]
                    )

                    for s in self.extract_subclauses(
                        clause.text
                    ):

                        sub = SubClause(
                            document="constitution",
                            sub_clause_no=s["sub_clause_no"],
                            text=s["text"]
                        )

                        for r in self.extract_roman_clauses(
                            sub.text
                        ):

                            sub.roman_clauses.append(
                                RomanClause(
                                    document="constitution",
                                    roman_no=r["roman_no"],
                                    text=r["text"]
                                )
                            )

                        clause.sub_clauses.append(sub)

                    article.clauses.append(clause)

                part.articles.append(article)

            parsed_parts.append(part)

        return parsed_parts


# ==========================================================
# EXAMPLE
# ==========================================================

if __name__ == "__main__":

    with open("text_extracted_ocr_output.txt", "r", encoding="utf8") as f:
        text = f.read()

    parser = ConstitutionParser()

    result = parser.parse(text)

    print(asdict(result[0]))