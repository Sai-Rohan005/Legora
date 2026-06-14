import re

class ConstitutionTextCleaner:
    def clean(
            self,
            text: str
        ) -> str:

            text = text.replace(
                "\r\n",
                "\n"
            )

            text = re.sub(
                r"\r",
                "\n",
                text
            )

            # remove page numbers

            text = re.sub(
                r"(?m)^\s*\d+\s*$",
                "",
                text
            )

            # remove repeated spaces

            text = re.sub(
                r"[ \t]+",
                " ",
                text
            )

            # remove constitution headers

            text = re.sub(
                r"THE CONSTITUTION OF INDIA",
                "",
                text,
                flags=re.I
            )

            # remove separators

            text = re.sub(
                r"_{3,}",
                "",
                text
            )

            # collapse blank lines

            text = re.sub(
                r"\n{3,}",
                "\n\n",
                text
            )

            return text.strip()
