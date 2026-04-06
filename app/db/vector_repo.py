from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.db.models import Task, Note, AgentMemory
from app.core.logging import get_logger

logger = get_logger(__name__)


class VectorRepository:
    """Semantic search over tasks, notes, and memories using pgvector cosine similarity."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def search_tasks(
        self, embedding: List[float], limit: int = 5, threshold: float = 0.7
    ) -> List[Task]:
        """Find tasks semantically similar to the query embedding."""
        try:
            result = await self.session.execute(
                select(Task)
                .where(Task.embedding.isnot(None))
                .order_by(Task.embedding.cosine_distance(embedding))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error("vector_search_tasks_failed", error=str(e))
            return []

    async def search_notes(
        self, embedding: List[float], limit: int = 5
    ) -> List[Note]:
        """Find notes semantically similar to the query embedding."""
        try:
            result = await self.session.execute(
                select(Note)
                .where(Note.embedding.isnot(None))
                .order_by(Note.embedding.cosine_distance(embedding))
                .limit(limit)
            )
            return list(result.scalars().all())
        except Exception as e:
            logger.error("vector_search_notes_failed", error=str(e))
            return []

    async def search_memories(
        self, embedding: List[float], agent_name: Optional[str] = None, limit: int = 3
    ) -> List[AgentMemory]:
        """Retrieve relevant agent memories for current context."""
        try:
            query = select(AgentMemory).where(AgentMemory.embedding.isnot(None))
            if agent_name:
                query = query.where(AgentMemory.agent_name == agent_name)
            query = query.order_by(AgentMemory.embedding.cosine_distance(embedding)).limit(limit)
            result = await self.session.execute(query)
            return list(result.scalars().all())
        except Exception as e:
            logger.error("vector_search_memories_failed", error=str(e))
            return []
