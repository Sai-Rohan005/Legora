from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import List, Optional


# =========================
# DATA MODEL
# =========================

@dataclass
class ConstitutionalChunk:
    chunk_id: str
    chunk_type: str  # part | article | clause

    part_no: Optional[str] = None
    part_title: Optional[str] = None

    article_no: Optional[str] = None
    article_title: Optional[str] = None

    clause_no: Optional[str] = None
    sub_clause_no: Optional[str] = None

    parent_id: Optional[str] = None

    text: str = ""
    embedding_text: str = ""


# =========================
# CHUNKER
# =========================

class ConstitutionChunker:
    """
    Production-grade Constitution of India chunker
    Hierarchy:
        PART → ARTICLE → CLAUSE
    """

    # FIXED: robust PART detection
    PART_RE = re.compile(
        r"(PART\s+[IVXLC]+)\s*\n+([^\n]+)",
        re.IGNORECASE
    )

    # FIXED: robust article detection
    ARTICLE_RE = re.compile(
        r"(?m)^(?:Article\s*)?(\d+[A-Z]?)\.?\s",
        re.IGNORECASE
    )

    # FIXED: clause detection
    CLAUSE_RE = re.compile(
        r"(?m)^\((\d+[A-Za-z]?)\)"
    )

    def uid(self):
        return str(uuid.uuid4())

    # =========================
    # CLEAN TEXT
    # =========================

    def normalize(self, text: str) -> str:
        text = re.sub(r"\r\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text.strip()

    # =========================
    # PART EXTRACTION
    # =========================

    def extract_parts(self, text: str):

        matches = list(self.PART_RE.finditer(text))
        parts = []

        for i, m in enumerate(matches):

            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            block = text[start:end].strip().split("\n")

            part_line = block[0].strip()
            part_title = block[1].strip() if len(block) > 1 else ""

            parts.append({
                "part_no": part_line.replace("PART", "").strip(),
                "part_title": part_title,
                "text": "\n".join(block).strip()
            })

        return parts

    # =========================
    # ARTICLE EXTRACTION
    # =========================

    def extract_articles(self, text: str):

        matches = list(self.ARTICLE_RE.finditer(text))
        articles = []

        for i, m in enumerate(matches):

            start = m.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            article_no = m.group(1)

            articles.append({
                "article_no": article_no,
                "text": text[start:end].strip()
            })

        return articles

    # =========================
    # MAIN CHUNKING
    # =========================

    def chunk(self, text: str) -> List[ConstitutionalChunk]:

        text = self.normalize(text)

        chunks: List[ConstitutionalChunk] = []

        parts = self.extract_parts(text)

        for part in parts:

            part_id = self.uid()

            # --------------------
            # PART CHUNK
            # --------------------
            chunks.append(
                ConstitutionalChunk(
                    chunk_id=part_id,
                    chunk_type="part",
                    part_no=part["part_no"],
                    part_title=part["part_title"],
                    text=part["text"],
                    embedding_text=f"""
PART {part['part_no']}
{part['part_title']}
""".strip()
                )
            )

            articles = self.extract_articles(part["text"])

            for article in articles:

                article_id = self.uid()

                # --------------------
                # ARTICLE CHUNK
                # --------------------
                chunks.append(
                    ConstitutionalChunk(
                        chunk_id=article_id,
                        chunk_type="article",
                        parent_id=part_id,
                        part_no=part["part_no"],
                        article_no=article["article_no"],
                        text=article["text"],
                        embedding_text=f"""
PART {part['part_no']}

ARTICLE {article['article_no']}

{article['text']}
""".strip()
                    )
                )

                # --------------------
                # CLAUSES
                # --------------------
                clause_matches = list(
                    re.finditer(r"(?m)^\((\d+[A-Za-z]?)\)", article["text"])
                )

                for j, cm in enumerate(clause_matches):

                    start = cm.start()
                    end = clause_matches[j + 1].start() if j + 1 < len(clause_matches) else len(article["text"])

                    clause_block = article["text"][start:end].strip()

                    clause_no = cm.group(1)

                    clause_id = self.uid()

                    # IMPORTANT: CLEAN clause text only
                    clause_text = clause_block

                    chunks.append(
                        ConstitutionalChunk(
                            chunk_id=clause_id,
                            chunk_type="clause",
                            parent_id=article_id,
                            part_no=part["part_no"],
                            article_no=article["article_no"],
                            clause_no=clause_no,
                            text=clause_text,
                            embedding_text=f"""
PART {part['part_no']}

ARTICLE {article['article_no']}

CLAUSE ({clause_no})

{clause_text}
""".strip()
                        )
                    )

        return chunks


# =========================
# TEST
# =========================

if __name__ == "__main__":

    sample_text = """
PART III
FUNDAMENTAL RIGHTS

Right to Equality

14. Equality before law.

15. Prohibition of discrimination.

Right to Freedom

19. Protection of speech.

(1) All citizens shall have the right—

(a) freedom of speech and expression;

(b) to assemble peaceably;

(2) Reasonable restrictions may apply.
"""

    chunker = ConstitutionChunker()
    chunks = chunker.chunk(sample_text)

    print(f"\nTotal chunks: {len(chunks)}\n")

    for c in chunks:
        print("=" * 80)
        print("TYPE:", c.chunk_type)
        print("PART:", c.part_no)
        print("ARTICLE:", c.article_no)
        print("CLAUSE:", c.clause_no)
        print("PARENT:", c.parent_id)
        print(c.embedding_text)