import requests
import logging
from legora.config import get_settings

from google import genai
from google.genai import types


logger = logging.getLogger(__name__)


class LegalQueryRewriter:

    def __init__(self, api_key):

        self.model = get_settings().gemini_model
        self.client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=int(get_settings().external_timeout_seconds * 1000), retry_options=types.HttpRetryOptions(attempts=1))
        )

    def rewrite(
        self,
        query: str
    ):

        prompt = f"""
You are an Indian legal search expert.

Convert the user question into a concise legal search query suitable for Indian Kanoon.

Rules:
- Include legal concepts.
- Include section names if obvious.
- Remove conversational words.
- Return ONLY the search query.

Question:
{query}
"""

        response = (
            self.client.models.generate_content(
                model=self.model,
                contents=prompt
            )
        )

        return response.text.strip()


class KanoonClient:

    def __init__(self):

        settings = get_settings()
        self.token = settings.kanoon_token.get_secret_value()

        self.headers = {
            "Authorization":
                f"Token {self.token}"
        }

        self.rewriter = LegalQueryRewriter(
            api_key=settings.gemini_api_key.get_secret_value()
        )  

    def search(
        self,
        query: str
    ):

        url = (
            "https://api.indiankanoon.org/search/"
        )

        response = requests.post(
            url,
            headers=self.headers,
            data={
                "formInput": query
            },
            timeout=get_settings().external_timeout_seconds
        )

        response.raise_for_status()
        return response.json()

    def get_document(
        self,
        doc_id: str
    ):

        url = (
            f"https://api.indiankanoon.org/doc/{doc_id}/"
        )

        response = requests.get(
            url,
            headers=self.headers,
            timeout=get_settings().external_timeout_seconds
        )

        response.raise_for_status()
        return response.json()
    

    def retrieve(self, query: str, top_k: int | None = None):
        top_k = top_k if top_k is not None else get_settings().judgment_k

        kanoon_query = self.rewriter.rewrite(query) or query

        search_results = self.search(kanoon_query)

        judgments = []

        for doc in search_results.get("docs", [])[:top_k]:

            doc_id = doc.get("tid") or doc.get("id")

            if not doc_id:
                continue

            full_doc = self.get_document(doc_id)
            full_doc.setdefault("tid", str(doc_id))
            judgments.append(full_doc)

        return judgments