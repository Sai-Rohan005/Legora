from abc import ABC, abstractmethod
import re


class BaseLegalParser(ABC):

    # ----------------------------------
    # REFERENCES
    # ----------------------------------

    REFERENCE_RE = re.compile(
        r"(?:article|section)[s]?\s+(\d+[A-Z]?)",
        re.IGNORECASE
    )

    # ----------------------------------
    # LEGAL HIERARCHY
    # ----------------------------------

    CLAUSE_RE = re.compile(
        r"(?m)^\((\d+[A-Za-z]?)\)\s*(.*)"
    )

    SUBCLAUSE_RE = re.compile(
        r"(?m)^\(([a-z])\)\s*(.*)"
    )

    ROMAN_RE = re.compile(
        r"(?m)^\((i|ii|iii|iv|v|vi|vii|viii|ix|x)\)\s*(.*)"
    )

    # ----------------------------------
    # CLEANER
    # ----------------------------------

    def clean(self, text: str):

        text = text.replace("\r\n", "\n")

        text = re.sub(
            r"(?m)^\s*\d+\s*$",
            "",
            text
        )

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()

    # ----------------------------------
    # REFERENCES
    # ----------------------------------

    def extract_references(self, text):

        return sorted(
            set(
                self.REFERENCE_RE.findall(text)
            )
        )

    # ----------------------------------
    # CLAUSES  (1) (2) (3)
    # ----------------------------------

    def extract_clauses(self, text):

        matches = list(
            self.CLAUSE_RE.finditer(text)
        )

        results = []

        for i, m in enumerate(matches):

            start = m.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append(
                {
                    "clause_no": m.group(1),
                    "text": text[start:end].strip()
                }
            )

        return results

    # ----------------------------------
    # SUBCLAUSES (a)(b)(c)
    # ----------------------------------

    def extract_subclauses(self, text):

        matches = list(
            self.SUBCLAUSE_RE.finditer(text)
        )

        results = []

        for i, m in enumerate(matches):

            start = m.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append(
                {
                    "sub_clause_no": m.group(1),
                    "text": text[start:end].strip()
                }
            )

        return results

    # ----------------------------------
    # ROMAN CLAUSES (i)(ii)(iii)
    # ----------------------------------

    def extract_roman_clauses(self, text):

        matches = list(
            self.ROMAN_RE.finditer(text)
        )

        results = []

        for i, m in enumerate(matches):

            start = m.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            results.append(
                {
                    "roman_no": m.group(1),
                    "text": text[start:end].strip()
                }
            )

        return results

    # ----------------------------------
    # ABSTRACT
    # ----------------------------------

    @abstractmethod
    def parse(self, text):
        pass