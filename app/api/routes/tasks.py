from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import Optional, List

from app.api.schemas import TaskCreate, TaskUpdate, TaskResponse, SemanticSearchRequest, SemanticSearchResponse
from app.db.database import get_db
from app.db.models import Task
from app.db.vector_repo import VectorRepository
from app.tools.embedding_tool import generate_embedding, generate_query_embedding
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a task and generate a semantic embedding for it."""
    task = Task(
        title=body.title,
        description=body.description,
        status=body.status,
        priority=body.priority,
        due_date=body.due_date,
        tags=body.tags,
    )

    # Generate embedding for semantic search
    embed_text = f"{body.title} {body.description or ''} {' '.join(body.tags or [])}"
    task.embedding = await generate_embedding(embed_text)

    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List tasks with optional filters."""
    query = select(Task).order_by(Task.created_at.desc()).limit(limit)
    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(task_id: UUID, body: TaskUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(task, field, value)

    # Re-embed if title or description changed
    if body.title or body.description:
        embed_text = f"{task.title} {task.description or ''}"
        task.embedding = await generate_embedding(embed_text)

    await db.flush()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)


@router.post("/search/semantic", response_model=SemanticSearchResponse)
async def semantic_search(body: SemanticSearchRequest, db: AsyncSession = Depends(get_db)):
    """
    Semantic search over tasks and notes using pgvector cosine similarity.
    Far more powerful than keyword search — finds conceptually related items.
    """
    embedding = await generate_query_embedding(body.query)
    if not embedding:
        raise HTTPException(status_code=500, detail="Failed to generate query embedding")

    repo = VectorRepository(db)
    tasks = []
    notes = []

    if body.search_type in ("tasks", "all"):
        tasks = await repo.search_tasks(embedding, limit=body.limit)
    if body.search_type in ("notes", "all"):
        notes = await repo.search_notes(embedding, limit=body.limit)

    return SemanticSearchResponse(
        query=body.query,
        tasks=tasks,
        notes=notes,
        total_results=len(tasks) + len(notes),
    )
