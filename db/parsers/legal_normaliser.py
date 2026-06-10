from parser import Clause, RomanClause, SubClause
from models.legal_models import (
LegalDocument,
Division,
Provision
)

class LegalNormalizer:


    def normalize(
        self,
        parsed_data,
        document_type: str
    ) -> LegalDocument:

        if document_type == "constitution":
            return self._constitution(parsed_data)

        if document_type == "bns":
            return self._bns(parsed_data)

        if document_type == "bnss":
            return self._bnss(parsed_data)

        if document_type == "bsa":
            return self._bsa(parsed_data)

        raise ValueError(
            f"Unsupported document type: {document_type}"
        )

    # ==========================================
    # CONSTITUTION
    # ==========================================

    def _constitution(self, parts):

        divisions = []

        for part in parts:

            division = Division(
                division_no=part.part_no,
                title=getattr(part, "part_title", None) or "",
                provisions=[]
            )

            articles = getattr(part, "articles", None) or []

            for article in articles:

                provision = Provision(
                    provision_no=article.article_no,
                    title=article.article_title,
                    text=article.text,
                    clauses=getattr(article, "clauses", []) or [],
                    provisos=getattr(article, "provisos", []) or [],
                    explanations=getattr(article, "explanations", []) or [],
                    references=getattr(article, "references", []) or []
                )

                division.provisions.append(provision)

            divisions.append(division)

        return LegalDocument(
            document_type="constitution",
            divisions=divisions
        )

    # ==========================================
    # BNS
    # ==========================================

    def _bns(self, chapters):

        divisions = []

        for chapter in chapters:

            division = Division(
                division_no=chapter.chapter_no,
                title=chapter.chapter_title,
                provisions=[]
            )

            for section in chapter.sections:

                provision = Provision(
                    provision_no=section.section_no,
                    title=section.section_title,
                    text=section.text,
                    clauses=[]
                )

                # IMPORTANT: deep copy clauses properly
                for clause in section.clauses:

                    new_clause = Clause(
                        clause_no=clause.clause_no,
                        text=clause.text,
                        sub_clauses=[]
                    )

                    for sub in clause.sub_clauses:

                        new_sub = SubClause(
                            sub_clause_no=sub.sub_clause_no,
                            text=sub.text,
                            roman_clauses=[]
                        )

                        for roman in sub.roman_clauses:
                            new_sub.roman_clauses.append(
                                RomanClause(
                                    roman_no=roman.roman_no,
                                    text=roman.text
                                )
                            )

                        new_clause.sub_clauses.append(new_sub)

                    provision.clauses.append(new_clause)

                division.provisions.append(provision)

            divisions.append(division)

        return LegalDocument(
            document_type="bns",
            divisions=divisions
        )

    # ==========================================
    # BNSS
    # ==========================================

    def _bnss(self, chapters):

        divisions = []

        for chapter in chapters:

            division = Division(
                division_no=chapter.chapter_no,
                title=chapter.chapter_title,
                provisions=[]
            )

            for section in chapter.sections:

                provision = Provision(
                    provision_no=section.section_no,
                    title=section.section_title,
                    text=section.text,
                    clauses=section.clauses,
                    provisos=[],
                    explanations=[],
                    illustrations=[],
                    references=[]
                )

                division.provisions.append(provision)

            divisions.append(division)

        return LegalDocument(
            document_type="bnss",
            divisions=divisions
        )

    # ==========================================
    # BSA
    # ==========================================

    def _bsa(self, parts):

        divisions = []

        for part in parts:

            for chapter in part.chapters:

                division = Division(
                    division_type="chapter",
                    division_no=chapter.chapter_no,
                    title=chapter.chapter_title
                )

                for section in chapter.sections:

                    provision = Provision(
                        provision_no=section.section_no,
                        title=section.section_title,
                        text=section.text,
                        clauses=section.clauses
                    )

                    division.provisions.append(
                        provision
                    )

                divisions.append(
                    division
                )

        return LegalDocument(
            document_type="bsa",
            divisions=divisions
        )

