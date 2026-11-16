from __future__ import annotations

from google import genai
from google.genai import types
from legora.config import get_settings


class LegalLLM:

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None
    ):
        settings = get_settings()
        self.model = model or settings.gemini_model
        self.client = genai.Client(
            api_key=api_key or settings.gemini_api_key.get_secret_value(),
            http_options=types.HttpOptions(timeout=int(settings.external_timeout_seconds * 1000), retry_options=types.HttpRetryOptions(attempts=1))
        )

    # =====================================================
    # GENERATE
    # =====================================================

    def generate(
        self,
        query: str,
        context: str,
        **kwargs
    ) -> str:
        """
        Generate a legal answer using the provided context.
        
        Args:
            query: User's legal question.
            context: Retrieved legal context (statutes, judgments, graph).
            **kwargs: Additional generation parameters (temperature, max_tokens, etc.)
                     passed directly to the Gemini API.
        
        Returns:
            The generated answer as a string.
        """
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

        # Prepare generation config from kwargs
        # Allowed parameters: temperature, max_tokens, top_p, top_k, etc.
        # We'll pass them as keyword arguments to generate_content.
        # Gemini's generate_content accepts a 'config' parameter with these.
        # We'll build a config dict from kwargs.
        config = {}
        if "temperature" in kwargs:
            config["temperature"] = kwargs["temperature"]
        if "max_tokens" in kwargs:
            config["max_output_tokens"] = kwargs["max_tokens"]
        if "top_p" in kwargs:
            config["top_p"] = kwargs["top_p"]
        if "top_k" in kwargs:
            config["top_k"] = kwargs["top_k"]
        # Add any other supported parameters as needed

        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config if config else None  # only pass config if non-empty
        )

        return response.text