from __future__ import annotations

import uuid
from typing import List, Dict, Any


class ConstitutionRecordGenerator:
    """
    Converts parsed Constitution hierarchy into
    Qdrant-ready records.

    Output:
    [
        {
            "id": "...",
            "chunk_type": "article",
            "embedding_text": "...",
            "metadata": {...}
        }
    ]
    """

    def generate(self, parts) -> List[Dict[str, Any]]:

        records = []

        for part in parts:

            for article in part.articles:

                # ====================================
                # ARTICLE RECORD
                # ====================================

                records.append(
                    self._article_record(
                        part,
                        article
                    )
                )

                # ====================================
                # CLAUSE RECORDS
                # ====================================

                for clause in article.clauses:

                    records.append(
                        self._clause_record(
                            part,
                            article,
                            clause
                        )
                    )

                    # ================================
                    # SUBCLAUSE RECORDS
                    # ================================

                    for sub in clause.sub_clauses:

                        records.append(
                            self._subclause_record(
                                part,
                                article,
                                clause,
                                sub
                            )
                        )

                        # ============================
                        # ROMAN CLAUSE RECORDS
                        # ============================

                        for roman in sub.roman_clauses:

                            records.append(
                                self._roman_record(
                                    part,
                                    article,
                                    clause,
                                    sub,
                                    roman
                                )
                            )

                # ====================================
                # PROVISO RECORDS
                # ====================================

                for proviso in article.provisos:

                    records.append(
                        self._proviso_record(
                            part,
                            article,
                            proviso
                        )
                    )

                # ====================================
                # EXPLANATION RECORDS
                # ====================================

                for explanation in article.explanations:

                    records.append(
                        self._explanation_record(
                            part,
                            article,
                            explanation
                        )
                    )

        return records

    # ==================================================
    # ARTICLE
    # ==================================================

    def _article_record(
        self,
        part,
        article
    ):

        return {
            "id": str(uuid.uuid4()),

            "chunk_type": "article",

            "embedding_text": f"""
Part {part.part_no}

{part.part_title}

Article {article.article_no}

{article.article_title}

{article.text}
""".strip(),

            "metadata": {
                "part_no": part.part_no,
                "part_title": part.part_title,

                "article_no": article.article_no,
                "article_title": article.article_title,

                "chunk_type": "article",

                "references": [
                    r.article_no
                    for r in article.references
                ]
            }
        }

    # ==================================================
    # CLAUSE
    # ==================================================

    def _clause_record(
        self,
        part,
        article,
        clause
    ):

        return {
            "id": str(uuid.uuid4()),

            "chunk_type": "clause",

            "embedding_text": f"""
Part {part.part_no}

{part.part_title}

Article {article.article_no}

{article.article_title}

Clause ({clause.clause_no})

{clause.text}
""".strip(),

            "metadata": {
                "part_no": part.part_no,
                "part_title": part.part_title,

                "article_no": article.article_no,
                "article_title": article.article_title,

                "clause_no": clause.clause_no,

                "chunk_type": "clause"
            }
        }

    # ==================================================
    # SUB CLAUSE
    # ==================================================

    def _subclause_record(
        self,
        part,
        article,
        clause,
        sub
    ):

        return {
            "id": str(uuid.uuid4()),

            "chunk_type": "sub_clause",

            "embedding_text": f"""
Part {part.part_no}

{part.part_title}

Article {article.article_no}

{article.article_title}

Clause ({clause.clause_no})

Sub-Clause ({sub.sub_clause_no})

{sub.text}
""".strip(),

            "metadata": {
                "part_no": part.part_no,
                "part_title": part.part_title,

                "article_no": article.article_no,
                "article_title": article.article_title,

                "clause_no": clause.clause_no,

                "sub_clause_no":
                    sub.sub_clause_no,

                "chunk_type":
                    "sub_clause"
            }
        }

    # ==================================================
    # ROMAN CLAUSE
    # ==================================================

    def _roman_record(
        self,
        part,
        article,
        clause,
        sub,
        roman
    ):

        return {
            "id": str(uuid.uuid4()),

            "chunk_type": "roman_clause",

            "embedding_text": f"""
Part {part.part_no}

{part.part_title}

Article {article.article_no}

{article.article_title}

Clause ({clause.clause_no})

Sub-Clause ({sub.sub_clause_no})

Roman Clause ({roman.roman_no})

{roman.text}
""".strip(),

            "metadata": {
                "part_no": part.part_no,

                "article_no":
                    article.article_no,

                "clause_no":
                    clause.clause_no,

                "sub_clause_no":
                    sub.sub_clause_no,

                "roman_no":
                    roman.roman_no,

                "chunk_type":
                    "roman_clause"
            }
        }

    # ==================================================
    # PROVISO
    # ==================================================

    def _proviso_record(
        self,
        part,
        article,
        proviso
    ):

        return {
            "id": str(uuid.uuid4()),

            "chunk_type": "proviso",

            "embedding_text": f"""
Part {part.part_no}

{part.part_title}

Article {article.article_no}

{article.article_title}

Proviso

{proviso.text}
""".strip(),

            "metadata": {
                "part_no": part.part_no,

                "article_no":
                    article.article_no,

                "chunk_type":
                    "proviso"
            }
        }

    # ==================================================
    # EXPLANATION
    # ==================================================

    def _explanation_record(
        self,
        part,
        article,
        explanation
    ):

        return {
            "id": str(uuid.uuid4()),

            "chunk_type": "explanation",

            "embedding_text": f"""
Part {part.part_no}

{part.part_title}

Article {article.article_no}

{article.article_title}

Explanation

{explanation.text}
""".strip(),

            "metadata": {
                "part_no": part.part_no,

                "article_no":
                    article.article_no,

                "chunk_type":
                    "explanation"
            }
        }