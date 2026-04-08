from typing import List, Optional
from google import genai
from google.genai import types
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

# Use newer google-genai client (v1 API, not v1beta)
_client = genai.Client(api_key=settings.gemini_api_key)

EMBEDDING_MODEL = "text-embedding-004"
EMBEDDING_DIM = 768


async def generate_embedding(text: str) -> Optional[List[float]]:
    """
    Generate a 768-dim embedding vector for the given text using Gemini.
    """
    try:
        result = _client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.error("embedding_generation_failed", error=str(e), text_preview=text[:100])
        return None


async def generate_query_embedding(query: str) -> Optional[List[float]]:
    """
    Generate a query-optimized embedding for semantic search.
    """
    try:
        result = _client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
        )
        return result.embeddings[0].values
    except Exception as e:
        logger.error("query_embedding_failed", error=str(e))
        return None
