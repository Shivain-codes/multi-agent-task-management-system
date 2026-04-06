from typing import List, Optional
import google.generativeai as genai
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

genai.configure(api_key=settings.gemini_api_key)

EMBEDDING_MODEL = "models/embedding-001"
EMBEDDING_DIM = 768


async def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate a 768-dim embedding vector for the given text using Gemini.

    Args:
        text: Input text to embed

    Returns:
        List of floats (768 dimensions), or None on failure
    """
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type="retrieval_document",
        )
        return result["embedding"]
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e), text_preview=text[:100])
        return None


async def generate_query_embedding(query: str) -> Optional[List[float]]:
    """
    Generate a query-optimized embedding for semantic search.

    Args:
        query: Search query string

    Returns:
        List of floats, or None on failure
    """
    try:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=query,
            task_type="retrieval_query",
        )
        return result["embedding"]
    except Exception as e:
        logger.error("query_embedding_failed", error=str(e))
        return None
