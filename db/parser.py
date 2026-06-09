from __future__ import annotations

import re
from typing import List, Dict, Any


class LegalParser:
    """
    Converts raw Constitution text into structured legal JSON.
    """

    PART_PATTERN = re.compile(
        r"PART\s+([IVXLC]+)\s*\n([^\n]+)",
        re.IGNORECASE
    )

    ARTICLE_PATTERN = re.compile(
        r"(?m)^(?:Article\s*)?(\d+[A-Z]?)\.?\s*(.+)"
    )

    CLAUSE_PATTERN = re.compile(
        r"(?m)^\((\d+[A-Za-z]?)\)\s*(.+)?"
    )

    def normalize(self, text: str) -> str:
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    # ---------------------------
    # MAIN PARSE FUNCTION
    # ---------------------------

    def parse(self, text: str) -> Dict[str, Any]:

        text = self.normalize(text)

        parts = list(self.PART_PATTERN.finditer(text))

        structured = {
            "parts": []
        }

        for i, part_match in enumerate(parts):

            start = part_match.start()
            end = parts[i + 1].start() if i + 1 < len(parts) else len(text)

            part_block = text[start:end]

            part_no = part_match.group(1)
            part_title = part_match.group(2).strip()

            part_data = {
                "part_no": part_no,
                "part_title": part_title,
                "articles": []
            }

            # -----------------------
            # ARTICLE SPLIT
            # -----------------------
            article_blocks = self.split_articles(part_block)

            for article_no, article_text in article_blocks:

                article_data = {
                    "article_no": article_no,
                    "text": article_text.strip(),
                    "clauses": self.extract_clauses(article_text)
                }

                part_data["articles"].append(article_data)

            structured["parts"].append(part_data)

        return structured

    # ---------------------------
    # ARTICLE SPLITTER
    # ---------------------------

    def split_articles(self, text: str) -> List[tuple]:

        matches = list(self.ARTICLE_PATTERN.finditer(text))
        articles = []

        for i, m in enumerate(matches):

            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            article_no = m.group(1)
            article_text = text[start:end]

            articles.append((article_no, article_text))

        return articles

    # ---------------------------
    # CLAUSE EXTRACTOR
    # ---------------------------

    def extract_clauses(self, text: str):

        # remove article number/title line
        text = re.sub(r"^\d+[A-Z]?\.\s.*\n?", "", text, flags=re.MULTILINE)

        matches = list(self.CLAUSE_PATTERN.finditer(text))

        clauses = []

        for i, m in enumerate(matches):

            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            clause_no = m.group(1)
            clause_text = text[start:end].strip()

            clauses.append({
                "clause_no": clause_no,
                "text": clause_text
            })

        return clauses
    
    
    def parse_file(self, file_path: str):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        return self.parse(text)

