
from __future__ import annotations

import re
from typing import List

from db.parsers.consitution.legal_models import Proviso


class ProvisoParser:

    """
    Legal Proviso Parser

    Supports:

        Provided that

        Provided further that

        Provided also that

        Provided further also that
    """

    # =====================================================
    # PROVISO PATTERN
    # =====================================================

    PROVISO_RE = re.compile(
        r"""
        (
            Provided
            (?:
                \s+further
            )?
            (?:
                \s+also
            )?
            \s+that

            .*?
        )

        (?=

            Provided
            (?:
                \s+further
            )?
            (?:
                \s+also
            )?
            \s+that

            |

            Explanation

            |

            Illustration

            |

            $
        )
        """,
        re.IGNORECASE
        | re.DOTALL
        | re.VERBOSE
    )

    # =====================================================
    # CLEANER
    # =====================================================

    def clean_text(
        self,
        text: str
    ) -> str:

        text = text.strip()

        text = re.sub(
            r"\s+",
            " ",
            text
        )

        return text

    # =====================================================
    # PARSE PROVISOS
    # =====================================================

    def parse_provisos(
        self,
        article_text: str
    ) -> List[Proviso]:

        provisos = []

        matches = (
            self.PROVISO_RE.findall(
                article_text
            )
        )

        for match in matches:

            provisos.append(
                Proviso(
                    document="constitution",
                    text=self.clean_text(
                        match
                    )
                )
            )

        return provisos

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_provisos(
        self,
        provisos: List[Proviso]
    ) -> List[str]:

        errors = []

        for i, proviso in enumerate(
            provisos
        ):

            if not proviso.text:

                errors.append(
                    f"Empty Proviso {i}"
                )

            if len(
                proviso.text
            ) < 15:

                errors.append(
                    f"Suspiciously Short "
                    f"Proviso {i}"
                )

        return errors


# =========================================================
# EXAMPLE
# =========================================================

if __name__ == "__main__":

    sample = """
    The State may make laws.

    Provided that no citizen
    shall be denied access.

    Provided further that
    Parliament may regulate.

    Explanation I.—
    This provision applies...
    """

    parser = ProvisoParser()

    provisos = (
        parser.parse_provisos(
            sample
        )
    )

    print(
        f"Found "
        f"{len(provisos)} "
        f"provisos"
    )

    for p in provisos:

        print()
        print(p.text)

    print(
        parser.validate_provisos(
            provisos
        )
    )
