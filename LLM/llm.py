from __future__ import annotations

from google import genai


class LegalLLM:

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash-lite"
    ):

        self.model = model

        self.client = genai.Client(
            api_key=api_key
        )

    # =====================================================
    # GENERATE
    # =====================================================

    def generate(
        self,
        query: str,
        context: str
    ):

        prompt = f"""
You are an expert Indian Legal Assistant.

Use ONLY the supplied legal context.

If the answer is not found in the context,
say:

"The provided legal corpus does not contain
sufficient information to answer this question."

Question:
{query}

Legal Context:
{context}

Answer:
"""

        response = (
            self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
        )

        return response.text