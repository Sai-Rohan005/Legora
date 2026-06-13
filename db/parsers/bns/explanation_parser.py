from __future__ import annotations

import re
from typing import List, Optional

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
        r"(?im)^Explanation\s*([0-9IVXLCDM]*)\s*[\.\-—:]"
    )

    # =====================================================
    # ROMAN NUMERAL NORMALIZATION
    # =====================================================

    ROMAN_MAP = {
        "I": "1",
        "II": "2",
        "III": "3",
        "IV": "4",
        "V": "5",
        "VI": "6",
        "VII": "7",
        "VIII": "8",
        "IX": "9",
        "X": "10",
        "XI": "11",
        "XII": "12",
        "XIII": "13",
        "XIV": "14",
        "XV": "15",
        "XVI": "16",
        "XVII": "17",
        "XVIII": "18",
        "XIX": "19",
        "XX": "20",
    }

    def normalize_explanation_no(
        self,
        explanation_no: str
    ) -> Optional[str]:

        explanation_no = explanation_no.strip().upper()

        if not explanation_no:
            return None

        return self.ROMAN_MAP.get(
            explanation_no,
            explanation_no
        )

    # =====================================================
    # EXTRACT EXPLANATIONS
    # =====================================================

    def extract_explanations(
        self,
        text: str
    ) -> List[Explanation]:

        matches = list(
            self.EXPLANATION_RE.finditer(text)
        )

        if not matches:
            return []

        explanations = []

        for i, match in enumerate(matches):

            start = match.start()

            end = (
                matches[i + 1].start()
                if i + 1 < len(matches)
                else len(text)
            )

            explanation_no = self.normalize_explanation_no(
                match.group(1)
            )

            explanation_text = (
                text[start:end]
                .strip()
            )

            explanations.append(
                Explanation(
                    document="bns",
                    explanation_no=explanation_no,
                    text=explanation_text
                )
            )

        return explanations

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_explanations(
        self,
        section_no,
        explanations: List[Explanation]
    ) -> List[str]:

        errors = []

        for explanation in explanations:

            if not explanation.text.strip():

                label = (
                    explanation.explanation_no
                    if explanation.explanation_no
                    else "Unnumbered"
                )

                errors.append(
                    f"Empty Explanation {label}"
                )

        return errors


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    sample = """
Whoever commits an offence shall be punished.

Explanation.—
This is an unnumbered explanation.

Explanation I.—
Roman numeral explanation.

Explanation 2.—
Second explanation.

Explanation II.—
Duplicate of Explanation 2.
"""

    parser = ExplanationParser()

    explanations = parser.extract_explanations(
        sample
    )

    print(
        "Explanations:",
        len(explanations)
    )

    print()

    for e in explanations:

        print(
            "Explanation No:",
            e.explanation_no
        )

        print(
            e.text
        )

        print(
            "-" * 60
        )

    errors = parser.validate_explanations(
        explanations
    )

    print()

    print(
        "Errors:",
        len(errors)
    )

    for error in errors:
        print(error)