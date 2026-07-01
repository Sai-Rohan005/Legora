from retrival.usage import LegalRetriever
from LLM.llm import LegalLLM
import os
import dotenv

dotenv.load_dotenv()

class RAGPipeline:

    def __init__(self):

        self.retriever = LegalRetriever()

        self.llm = LegalLLM(api_key=os.getenv("GEMINI_API_KEY"))

    # =====================================================
    # CONTEXT
    # =====================================================

    def get_context(
        self,
        query: str
    ):

        retrieval_result = (
            self.retriever.retrieve(
                query
            )
        )

        return retrieval_result

    # =====================================================
    # LLM
    # =====================================================

    def get_llm_result(
        self,
        query: str,
        context: str
    ):

        return self.llm.generate(
            query=query,
            context=context
        )

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query: str
    ):

        retrieval_result = (
            self.get_context(
                query
            )
        )

        context = retrieval_result[
            "final_context"
        ]
        print("=" * 100)
        print(retrieval_result["final_context"])
        print("=" * 100)

        answer = (
            self.get_llm_result(
                query,
                context
            )
        )

        return {
            "query": query,

            "answer": answer,

            "retrieval": retrieval_result
        }