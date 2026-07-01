from google import genai
from pydantic import BaseModel
from typing import List, Optional
import os
import dotenv

dotenv.load_dotenv()

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)

class LegalQueryAnalysis(BaseModel):
    query_type: str
    intent: str
    offence: Optional[str] = None
    legal_concepts: List[str]
    entities: List[str]
    acts: List[str]
    search_queries: List[str]


class Analyser:

    def __init__(self):
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

        response = client.models.generate_content(
            model=os.getenv("Gemini_MODEL"),
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

    print(analysis.model_dump())