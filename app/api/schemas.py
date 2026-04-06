from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


# ── Enums ─────────────────────────────────────────────────────────────────────

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# ── Workflow ──────────────────────────────────────────────────────────────────

class WorkflowRequest(BaseModel):
    request: str = Field(
        ...,
        min_length=5,
        max_length=2000,
        description="Natural language request for the AI system",
        examples=["I have a product launch next Friday. Block my calendar, create a checklist, write a brief, and notify the team on Slack."]
    )
    session_id: Optional[str] = Field(None, description="Optional session ID for multi-turn continuity")
    options: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional execution options")


class AgentStepResult(BaseModel):
    step: int
    agent: str
    success: bool
    duration_ms: Optional[int]
    summary: Optional[str]
    phase: str  # 'parallel' or 'sequential'


class WorkflowResponse(BaseModel):
    workflow_id: str
    session_id: str
    user_request: str
    status: str  # 'completed', 'partial', 'failed'
    summary: str
    steps: List[AgentStepResult]
    agents_used: List[str]
    duration_ms: int
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    tags: Optional[List[str]] = None


class TaskResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    tags: Optional[List[str]]
    asana_task_gid: Optional[str]
    workflow_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Schedules ─────────────────────────────────────────────────────────────────

class ScheduleCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: Optional[List[str]] = Field(default_factory=list)
    location: Optional[str] = None
    is_all_day: bool = False


class ScheduleResponse(BaseModel):
    id: UUID
    title: str
    description: Optional[str]
    start_time: datetime
    end_time: datetime
    attendees: Optional[List[str]]
    location: Optional[str]
    google_event_id: Optional[str]
    is_all_day: bool
    workflow_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Notes ─────────────────────────────────────────────────────────────────────

class NoteCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=1)
    tags: Optional[List[str]] = Field(default_factory=list)
    source: Optional[str] = "user"


class NoteResponse(BaseModel):
    id: UUID
    title: str
    content: str
    tags: Optional[List[str]]
    source: Optional[str]
    google_doc_id: Optional[str]
    workflow_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Semantic search ───────────────────────────────────────────────────────────

class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    search_type: str = Field("all", description="'tasks', 'notes', or 'all'")
    limit: int = Field(5, ge=1, le=20)


class SemanticSearchResponse(BaseModel):
    query: str
    tasks: List[TaskResponse] = []
    notes: List[NoteResponse] = []
    total_results: int


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    database: bool
    version: str = "1.0.0"
    environment: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Workflow trace (for /trace endpoint) ──────────────────────────────────────

class WorkflowTraceResponse(BaseModel):
    workflow_id: UUID
    session_id: str
    user_request: str
    status: str
    plan: Optional[Dict[str, Any]]
    steps: Optional[List[Dict[str, Any]]]
    result: Optional[Dict[str, Any]]
    duration_ms: Optional[int]
    agents_used: Optional[List[str]]
    created_at: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}
