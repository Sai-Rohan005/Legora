"""HTTP client shared by the Streamlit UI and its tests."""

import requests
from pydantic import ValidationError

from api.models import QueryResponse
from legora.config import get_client_settings


def query_api(query: str) -> dict:
    """Call the API with a deadline and expose only safe errors to the UI."""
    settings = get_client_settings()
    try:
        response = requests.post(
            settings.api_base_url.rstrip("/") + "/query",
            json={"query": query}, timeout=settings.api_timeout_seconds,
        )
        if response.status_code == 422:
            raise ValueError("The query was rejected. Enter a non-empty legal question.")
        response.raise_for_status()
        return QueryResponse.model_validate(response.json()).model_dump()
    except (requests.RequestException, ValidationError, requests.exceptions.JSONDecodeError):
        raise RuntimeError("The legal query service is unavailable. Please try again later.") from None
