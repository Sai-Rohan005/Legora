import re


class BNSSTextCleaner:

    @staticmethod
    def clean(text: str) -> str:

        # =====================================
        # Normalize line endings
        # =====================================

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # =====================================
        # Remove Gazette headers
        # Examples:
        #
        # THE GAZETTE OF INDIA EXTRAORDINARY
        # 46 THE GAZETTE OF INDIA EXTRAORDINARY
        # [PART II—
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
        # Remove notification footnotes
        # =====================================

        text = re.sub(
            r"(?im)^\d+\.\s+vide\s+notification.*?$",
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
        # Remove page numbers
        #
        # 46
        # 127
        # =====================================

        text = re.sub(
            r"(?m)^\d+\s*$",
            "",
            text
        )

        # =====================================
        # Remove standalone section numbers
        #
        # 150.
        # 230.
        # 409.
        #
        # Keeps:
        # 150. Police may...
        # =====================================

        text = re.sub(
            r"(?m)^\d+\.\s*$",
            "",
            text
        )

        # =====================================
        # Remove OCR underscore blocks
        # =====================================

        text = re.sub(
            r"(?m)^[_ ]{20,}$",
            "",
            text
        )

        # =====================================
        # Remove excessive spaces
        # =====================================

        text = re.sub(
            r"[ \t]+",
            " ",
            text
        )

        # =====================================
        # Collapse empty lines
        # =====================================

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text
        )

        return text.strip()