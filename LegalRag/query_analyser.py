import logging
from google import genai
from pydantic import BaseModel
from typing import List, Optional
from legora.config import get_settings

logger = logging.getLogger(__name__)


class LegalQueryAnalysis(BaseModel):
    query_type: str
    intent: str
    offence: Optional[str] = None
    legal_concepts: List[str]
    entities: List[str]
    acts: List[str]
    search_queries: List[str]


class Analyser:

    def __init__(self) -> None:
        """Create the analyser with the shared Gemini configuration."""
        settings = get_settings()
        self.model = settings.gemini_model
        self.client = genai.Client(api_key=settings.gemini_api_key.get_secret_value())
        self.SYSTEM_PROMPT = """
        You are an expert Indian legal query analyzer.

        Your job is NOT to answer legal questions.

        Your job is to extract structured retrieval metadata
        for a Legal RAG system.

        Identify:

        1. query_type
        - criminal
        - civil
        - constitutional
        - evidence
        - procedural
        - judgment

        2. intent
        - punishment
        - definition
        - rights
        - procedure
        - evidence
        - remedy
        - bail
        - appeal

        3. offence (if applicable)

        4. legal concepts

        5. relevant acts
        - BNS
        - BNSS
        - BSA
        - Constitution

        6. search queries for retrieval

        Return only structured data.
        """


    def analyze_query(self,query: str) -> LegalQueryAnalysis:

        response = self.client.models.generate_content(
            model=self.model,
            contents=f"""
        {self.SYSTEM_PROMPT}

        User Query:
        {query}
        """,
            config={
                "response_mime_type": "application/json",
                "response_schema": LegalQueryAnalysis,
                "temperature": 0
            }
        )

        return response.parsed
    

if __name__=="__main__":
    

    query = """
    My bike was stolen from outside my house.
    What punishment can the offender face?
    """
    analyser=Analyser()
    analysis = analyser.analyze_query(query)

    logger.debug('%s', analysis.model_dump())