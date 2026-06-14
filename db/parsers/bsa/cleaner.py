import re


class BSATextCleaner:

    @staticmethod
    def clean(text: str) -> str:

        # =====================================
        # Normalize line endings
        # =====================================

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # =====================================
        # Remove Gazette headers
        # =====================================

        text = re.sub(
            r"(?im)^.*THE\s+GAZETTE\s+OF\s+INDIA\s+EXTRAORDINARY.*$\n?",
            "",
            text
        )

        # =====================================
        # Remove PART headers
        # =====================================

        text = re.sub(
            r"(?im)^\[?\s*PART\s+[IVXLC0-9A-Z\- ]+\]?\s*$",
            "",
            text
        )

        # =====================================
        # Remove Gazette footnotes
        # =====================================

        text = re.sub(
            r"(?im)^\d+\.\s+\d+(?:st|nd|rd|th)\s+day.*?$",
            "",
            text
        )

        # =====================================
        # Remove notification notes
        # =====================================

        text = re.sub(
            r"(?im)^\d+\.\s+vide\s+notification.*?$",
            "",
            text
        )

        # =====================================
        # Remove page numbers
        # =====================================

        text = re.sub(
            r"(?m)^\d+\s*$",
            "",
            text
        )

        # =====================================
        # Remove standalone page references
        #
        # 46.
        # 127.
        # =====================================

        text = re.sub(
            r"(?m)^\d+\.\s*$",
            "",
            text
        )

        # =====================================
        # Remove separator lines
        # =====================================

        text = re.sub(
            r"(?m)^[_=\-]{5,}\s*$",
            "",
            text
        )

        # =====================================
        # Remove OCR underline blocks
        # =====================================

        text = re.sub(
            r"(?m)^[_ ]{20,}$",
            "",
            text
        )

        # =====================================
        # Remove form-feed characters
        # =====================================

        text = text.replace(
            "\f",
            "\n"
        )

        # =====================================
        # Fix broken words
        #
        # exam-
        # ple
        # ->
        # example
        # =====================================

        text = re.sub(
            r"([a-zA-Z])-\n([a-zA-Z])",
            r"\1\2",
            text
        )

        # =====================================
        # Join OCR split words
        #
        # evi
        # dence
        #
        # only when lowercase
        # =====================================

        text = re.sub(
            r"([a-z])\n([a-z])",
            r"\1 \2",
            text
        )

        # =====================================
        # Normalize spaces
        # =====================================

        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # =====================================
        # Remove trailing spaces
        # =====================================

        text = re.sub(
            r"[ \t]+\n",
            "\n",
            text
        )

        # =====================================
        # Collapse blank lines
        # =====================================

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()