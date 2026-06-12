import re


class BNSTextCleaner:

    @staticmethod
    def clean(text: str) -> str:

        # Remove Gazette footnotes
        text = re.sub(
            r'(?m)^\d+\.\s+\d+(?:st|nd|rd|th)\s+day.*?$',
            '',
            text
        )

        # Remove page numbers
        text = re.sub(
            r'(?m)^\d+\s*$',
            '',
            text
        )

        # Remove standalone amendment notes
        text = re.sub(
            r'(?m)^\d+\.\s+vide notification.*?$',
            '',
            text,
            flags=re.I
        )

        # Collapse empty lines
        text = re.sub(
            r'\n{3,}',
            '\n\n',
            text
        )

        return text