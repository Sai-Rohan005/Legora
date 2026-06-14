from __future__ import annotations

import re
from typing import List

from legal_models import Illustration


class IllustrationParser:

    """
    Supports:

    Illustration.

    Illustrations.

    (a) ...
    (b) ...

    (i) ...
    (ii) ...

    or plain illustration text.
    """

    DOCUMENT = "bsa"

    # -------------------------------------------------
    # Illustration Header
    # -------------------------------------------------

    ILLUSTRATION_HEADER_RE = re.compile(
        r"(?im)^Illustrations?\.\s*$"
    )

    # -------------------------------------------------
    # Roman Illustration
    # -------------------------------------------------

    ROMAN_RE = re.compile(
        r"(?m)^\(([ivxlcdm]+)\)"
    )

    # -------------------------------------------------
    # Alphabet Illustration
    # -------------------------------------------------

    ALPHA_RE = re.compile(
        r"(?m)^\(([a-z])\)"
    )

    # =================================================
    # MAIN
    # =================================================

    def extract_illustrations(
        self,
        text: str
    ) -> List[Illustration]:

        header_match = (
            self.ILLUSTRATION_HEADER_RE.search(
                text
            )
        )

        if not header_match:
            return []

        illustration_text = (
            text[
                header_match.end():
            ]
            .strip()
        )

        illustrations = []

        # ============================================
        # Roman illustrations
        # ============================================

        roman_matches = list(
            self.ROMAN_RE.finditer(
                illustration_text
            )
        )

        if roman_matches:

            for i, match in enumerate(
                roman_matches
            ):

                start = match.start()

                end = (
                    roman_matches[i + 1].start()
                    if i + 1 < len(
                        roman_matches
                    )
                    else len(
                        illustration_text
                    )
                )

                illustrations.append(
                    Illustration(
                        document=
                            self.DOCUMENT,

                        illustration_no=
                            match.group(1),

                        text=
                            illustration_text[
                                start:end
                            ].strip()
                    )
                )

            return illustrations

        # ============================================
        # Alphabet illustrations
        # ============================================

        alpha_matches = list(
            self.ALPHA_RE.finditer(
                illustration_text
            )
        )

        if alpha_matches:

            for i, match in enumerate(
                alpha_matches
            ):

                start = match.start()

                end = (
                    alpha_matches[i + 1].start()
                    if i + 1 < len(
                        alpha_matches
                    )
                    else len(
                        illustration_text
                    )
                )

                illustrations.append(
                    Illustration(
                        document=
                            self.DOCUMENT,

                        illustration_no=
                            match.group(1),

                        text=
                            illustration_text[
                                start:end
                            ].strip()
                    )
                )

            return illustrations

        # ============================================
        # Single Illustration Block
        # ============================================

        illustrations.append(
            Illustration(
                document=
                    self.DOCUMENT,

                illustration_no=
                    None,

                text=
                    illustration_text
            )
        )

        return illustrations

    # =================================================
    # VALIDATION
    # =================================================

    def validate_illustrations(
        self,
        illustrations: List[Illustration]
    ) -> List[str]:

        errors = []

        seen = set()

        for illustration in illustrations:

            if not illustration.text.strip():

                errors.append(
                    "Empty Illustration"
                )

            if (
                illustration.illustration_no
                and illustration.illustration_no in seen
            ):

                errors.append(
                    f"Duplicate Illustration "
                    f"{illustration.illustration_no}"
                )

            if illustration.illustration_no:

                seen.add(
                    illustration.illustration_no
                )

        return errors