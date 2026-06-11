from models.legal_models import Clause, RomanClause, SubClause
from models.legal_models import (
    LegalDocument,
    Division,
    Provision
)


class LegalNormalizer:

    # =========================================================
    # MAIN ENTRY
    # =========================================================

    def normalize(self, parsed_data, document_type: str) -> LegalDocument:

        if document_type == "constitution":
            return self._constitution(parsed_data)

        if document_type == "bns":
            return self._bns(parsed_data)

        if document_type == "bnss":
            return self._bnss(parsed_data)

        if document_type == "bsa":
            return self._bsa(parsed_data)

        raise ValueError(f"Unsupported document type: {document_type}")

    # =========================================================
    # SAFE HELPERS
    # =========================================================

    def _safe_list(self, x):
        return x if isinstance(x, list) else []

    # =========================================================
    # CONSTITUTION
    # =========================================================

    def _constitution(self, parts):

        doc = "constitution"
        divisions = []

        for part in parts:

            division = Division(
                document=doc,
                division_no=part.part_no,
                title=getattr(part, "part_title", "") or "",
                provisions=[]
            )

            articles = self._safe_list(getattr(part, "articles", []))

            for article in articles:

                provision = Provision(
                    document=doc,
                    provision_no=article.article_no,
                    title=article.article_title,
                    text=article.text,
                    clauses=[],
                    provisos=[],
                    explanations=[],
                    references=[]
                )

                division.provisions.append(provision)

            divisions.append(division)

        return LegalDocument(
            document=doc,
            document_type=doc,
            divisions=divisions
        )

    # =========================================================
    # BNS (FULL HIERARCHY)
    # =========================================================

    def _bns(self, chapters):

        doc = "bns"
        divisions = []

        for chapter in chapters:

            division = Division(
                document=doc,
                division_no=chapter.chapter_no,
                title=chapter.chapter_title,
                provisions=[]
            )

            for section in self._safe_list(chapter.sections):

                provision = Provision(
                    document=doc,
                    provision_no=section.section_no,
                    title=section.section_title,
                    text=section.text,
                    clauses=[]
                )

                for clause in self._safe_list(section.clauses):

                    new_clause = Clause(
                        document=doc,
                        clause_no=clause.clause_no,
                        text=clause.text,
                        sub_clauses=[]
                    )

                    for sub in self._safe_list(clause.sub_clauses):

                        new_sub = SubClause(
                            document=doc,
                            sub_clause_no=sub.sub_clause_no,
                            text=sub.text,
                            roman_clauses=[]
                        )

                        for roman in self._safe_list(sub.roman_clauses):

                            new_sub.roman_clauses.append(
                                RomanClause(
                                    document=doc,
                                    roman_no=roman.roman_no,
                                    text=roman.text
                                )
                            )

                        new_clause.sub_clauses.append(new_sub)

                    provision.clauses.append(new_clause)

                division.provisions.append(provision)

            divisions.append(division)

        return LegalDocument(
            document=doc,
            document_type=doc,
            divisions=divisions
        )

    # =========================================================
    # BNSS (FIXED: FULL DEPTH SAME AS BNS)
    # =========================================================

    def _bnss(self, chapters):

        doc = "bnss"
        divisions = []

        for chapter in chapters:

            division = Division(
                document=doc,
                division_no=chapter.chapter_no,
                title=chapter.chapter_title,
                provisions=[]
            )

            for section in self._safe_list(chapter.sections):

                provision = Provision(
                    document=doc,
                    provision_no=section.section_no,
                    title=section.section_title,
                    text=section.text,
                    clauses=[]
                )

                for clause in self._safe_list(section.clauses):

                    new_clause = Clause(
                        document=doc,
                        clause_no=clause.clause_no,
                        text=clause.text,
                        sub_clauses=[]
                    )

                    for sub in self._safe_list(clause.sub_clauses):

                        new_sub = SubClause(
                            document=doc,
                            sub_clause_no=sub.sub_clause_no,
                            text=sub.text,
                            roman_clauses=[]
                        )

                        for roman in self._safe_list(sub.roman_clauses):

                            new_sub.roman_clauses.append(
                                RomanClause(
                                    document=doc,
                                    roman_no=roman.roman_no,
                                    text=roman.text
                                )
                            )

                        new_clause.sub_clauses.append(new_sub)

                    provision.clauses.append(new_clause)

                division.provisions.append(provision)

            divisions.append(division)

        return LegalDocument(
            document=doc,
            document_type=doc,
            divisions=divisions
        )

    # =========================================================
    # BSA (CONSISTENT STRUCTURE)
    # =========================================================

    def _bsa(self, parts):

        doc = "bsa"
        divisions = []

        for part in parts:

            for chapter in self._safe_list(part.chapters):

                division = Division(
                    document=doc,
                    division_no=chapter.chapter_no,
                    title=chapter.chapter_title,
                    provisions=[]
                )

                for section in self._safe_list(chapter.sections):

                    provision = Provision(
                        document=doc,
                        provision_no=section.section_no,
                        title=section.section_title,
                        text=section.text,
                        clauses=[]
                    )

                    for clause in self._safe_list(section.clauses):

                        new_clause = Clause(
                            document=doc,
                            clause_no=clause.clause_no,
                            text=clause.text,
                            sub_clauses=[]
                        )

                        # If BSA has deeper structure in future, you can extend here

                        provision.clauses.append(new_clause)

                    division.provisions.append(provision)

                divisions.append(division)

        return LegalDocument(
            document=doc,
            document_type=doc,
            divisions=divisions
        )