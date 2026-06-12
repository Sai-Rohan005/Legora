
from __future__ import annotations

import re
from typing import List

from legal_models import Explanation


class ExplanationParser:

    """
    Constitution / Legal Explanation Parser

    Supports:

        Explanation.—

        Explanation I.—

        Explanation II.—

        Explanation III.—

        Explanation 1.—

        Explanation 2.—
    """

    # =====================================================
    # EXPLANATION PATTERN
    # =====================================================

    EXPLANATION_RE = re.compile(
        r"""
        (

            Explanation

            (?:
                \s+
                (
                    [IVXLCDM]+
                    |
                    \d+
                )
            )?

            \s*
            [:\.\-—]*

            .*?

        )

        (?=

            Explanation

            (?:
                \s+
                (
                    [IVXLCDM]+
                    |
                    \d+
                )
            )?

            \s*
            [:\.\-—]

            |

            Illustration

            |

            Provided

            |

            $
        )
        """,
        re.IGNORECASE
        | re.DOTALL
        | re.VERBOSE
    )

    # =====================================================
    # CLEAN TEXT
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
    # EXTRACT NUMBER
    # =====================================================

    def extract_number(
        self,
        explanation_text: str
    ) -> str:

        m = re.match(
            r"""
            Explanation

            (?:
                \s+
                (
                    [IVXLCDM]+
                    |
                    \d+
                )
            )?
            """,
            explanation_text,
            re.IGNORECASE
            | re.VERBOSE
        )

        if not m:
            return ""

        return (
            m.group(1)
            if m.group(1)
            else ""
        )

    # =====================================================
    # PARSE EXPLANATIONS
    # =====================================================

    def parse_explanations(
        self,
        article_text: str
    ) -> List[Explanation]:

        explanations = []

        matches = list(
            self.EXPLANATION_RE.finditer(
                article_text
            )
        )

        for match in matches:

            text = self.clean_text(
                match.group(1)
            )

            explanation_no = (
                self.extract_number(
                    text
                )
            )

            explanations.append(
                Explanation(
                    document="constitution",
                    explanation_no=explanation_no,
                    text=text
                )
            )

        return explanations

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_explanations(
        self,
        explanations: List[Explanation]
    ) -> List[str]:

        errors = []

        seen = set()

        for exp in explanations:

            key = (
                exp.explanation_no
                or "__DEFAULT__"
            )

            if key in seen:

                errors.append(
                    f"Duplicate "
                    f"Explanation "
                    f"{key}"
                )

            seen.add(key)

            if not exp.text:

                errors.append(
                    f"Empty Explanation"
                )

            if len(exp.text) < 15:

                errors.append(
                    f"Suspiciously Short "
                    f"Explanation "
                    f"{key}"
                )

        return errors


# =========================================================
# EXAMPLE
# =========================================================

if __name__ == "__main__":

    sample = """
    Some legal provision.

    Explanation I.—
    For the purposes of this Article,
    the term citizen includes...

    Explanation II.—
    This shall not apply to...

    Provided that no person...
    """

    parser = ExplanationParser()

    explanations = (
        parser.parse_explanations(
            sample
        )
    )

    print(
        f"Found "
        f"{len(explanations)} "
        f"Explanations"
    )

    for e in explanations:

        print()
        print(
            "No:",
            e.explanation_no
        )

        print(
            e.text
        )

    print(
        parser.validate_explanations(
            explanations
        )
    )
