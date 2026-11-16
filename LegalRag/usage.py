import logging
from LegalRag.rag_pipeline import RAGPipeline

logger = logging.getLogger(__name__)


rag = RAGPipeline()

result = rag.search(
    "Can police arrest without warrant?"
)

logger.debug('%s', result["answer"])