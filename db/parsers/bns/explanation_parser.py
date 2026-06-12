from __future__ import annotations

import re
from typing import List

from legal_models import Explanation


class ExplanationParser:

    """
    BNS Explanation Parser

    Supports:

        Explanation.—

        Explanation 1.—

        Explanation 2.—

        Explanation I.—

        Explanation II.—
    """

    # =====================================================
    # REGEX
    # =====================================================

    EXPLANATION_RE = re.compile(
        r"(?im)^Explanation\s*([0-9IVXLCDM]*)\s*[.—:-]"
    )

    # =====================================================
    # SPLIT EXPLANATIONS
    # =====================================================

    def extract_explanations(
        self,
        text: str
    ) -> List[Explanation]:

        matches = list(
            self.EXPLANATION_RE.finditer(
                text
            )
        )

        if not matches:
            return []

        explanations = []

        for i, match in enumerate(
            matches
        ):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            explanation_no = (
                match.group(1).strip()
            )

            if not explanation_no:
                explanation_no = "1"

            explanation_text = (
                text[start:end]
                .strip()
            )

            explanations.append(
                Explanation(
                    document="bns",
                    explanation_no=
                        explanation_no,

                    text=
                        explanation_text
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

        for explanation in explanations:

            if (
                explanation.explanation_no
                in seen
            ):

                errors.append(
                    f"Duplicate "
                    f"Explanation "
                    f"{explanation.explanation_no}"
                )

            seen.add(
                explanation.explanation_no
            )

            if not (
                explanation.text
            ):

                errors.append(
                    f"Empty "
                    f"Explanation "
                    f"{explanation.explanation_no}"
                )

        return errors


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    sample = """
Whoever commits an offence shall be punished.

Explanation 1.—
For the purposes of this section,
"injury" includes harm illegally
caused to body, mind or reputation.

Explanation 2.—
A person may be liable even if
the consequence was unintended.
"""

    parser = ExplanationParser()

    explanations = (
        parser.extract_explanations(
            sample
        )
    )

    print(
        "Explanations:",
        len(explanations)
    )

    print()

    for e in explanations:

        print(
            e.explanation_no
        )

        print(
            e.text
        )

        print(
            "-" * 50
        )

    errors = (
        parser.validate_explanations(
            explanations
        )
    )

    print(
        "Errors:",
        len(errors)
    )