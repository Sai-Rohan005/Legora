from LegalRag.rag_pipeline import RAGPipeline


rag = RAGPipeline()

result = rag.search(
    "Can police arrest without warrant?"
)

print(result["answer"])