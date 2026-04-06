import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Boolean, DateTime, ForeignKey,
    Integer, Enum as SAEnum, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from app.db.database import Base
import enum


# ── Enums ─────────────────────────────────────────────────────────────────────

class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class WorkflowStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


# ── Models ────────────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    priority: Mapped[TaskPriority] = mapped_column(SAEnum(TaskPriority), default=TaskPriority.MEDIUM)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    tags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    asana_task_gid: Mapped[Optional[str]] = mapped_column(String(100))
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_traces.id"))
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768))  # Gemini embedding dim
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workflow: Mapped[Optional["WorkflowTrace"]] = relationship("WorkflowTrace", back_populates="tasks")


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attendees: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    location: Mapped[Optional[str]] = mapped_column(String(300))
    google_event_id: Mapped[Optional[str]] = mapped_column(String(200))
    is_all_day: Mapped[bool] = mapped_column(Boolean, default=False)
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_traces.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workflow: Mapped[Optional["WorkflowTrace"]] = relationship("WorkflowTrace", back_populates="schedules")


class Note(Base):
    __tablename__ = "notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    source: Mapped[Optional[str]] = mapped_column(String(100))  # 'user', 'agent', 'doc'
    google_doc_id: Mapped[Optional[str]] = mapped_column(String(200))
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("workflow_traces.id"))
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    workflow: Mapped[Optional["WorkflowTrace"]] = relationship("WorkflowTrace", back_populates="notes")


class AgentMemory(Base):
    """Persistent cross-session memory for agents."""
    __tablename__ = "agent_memory"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(50))  # 'episodic', 'semantic', 'procedural'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    memory_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector(768))
    ttl_hours: Mapped[Optional[int]] = mapped_column(Integer, default=168)  # 1 week default
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WorkflowTrace(Base):
    """Full execution trace for every multi-agent workflow."""
    __tablename__ = "workflow_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    user_request: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(SAEnum(WorkflowStatus), default=WorkflowStatus.RUNNING)
    plan: Mapped[Optional[dict]] = mapped_column(JSONB)          # orchestrator's decomposed plan
    steps: Mapped[Optional[list]] = mapped_column(JSONB, default=list)  # per-agent execution steps
    result: Mapped[Optional[dict]] = mapped_column(JSONB)        # final aggregated result
    error: Mapped[Optional[str]] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    agents_used: Mapped[Optional[list]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="workflow")
    schedules: Mapped[List["Schedule"]] = relationship("Schedule", back_populates="workflow")
    notes: Mapped[List["Note"]] = relationship("Note", back_populates="workflow")
