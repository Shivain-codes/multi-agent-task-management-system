from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.api.schemas import (
    WorkflowRequest,
    WorkflowResponse,
    WorkflowTraceResponse,
    AgentStepResult,
)
from app.agents.orchestrator import OrchestratorAgent
from app.db.database import get_db
from app.db.models import WorkflowTrace
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/workflows", tags=["Workflows"])


def get_orchestrator() -> OrchestratorAgent:
    """
    Lazily create the orchestrator at request time instead of import time.
    This avoids Cloud Run startup failures caused by deep import chains.
    """
    return OrchestratorAgent()


@router.post("/run", response_model=WorkflowResponse, summary="Run a multi-agent workflow")
async def run_workflow(
    body: WorkflowRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Execute a natural language request through the full Nexus multi-agent system.
    """
    try:
        orchestrator = get_orchestrator()

        result = await orchestrator.run(
            user_request=body.request,
            session_id=body.session_id,
            db_session=db,
        )

        return WorkflowResponse(
            workflow_id=result["workflow_id"],
            session_id=result["session_id"],
            user_request=result["user_request"],
            status=result["status"],
            summary=result["summary"],
            steps=[AgentStepResult(**s) for s in result["steps"]],
            agents_used=result["agents_used"],
            duration_ms=result["duration_ms"],
        )

    except Exception as e:
        logger.error("workflow_endpoint_failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@router.get(
    "/{workflow_id}/trace",
    response_model=WorkflowTraceResponse,
    summary="Get full execution trace for a workflow",
)
async def get_workflow_trace(
    workflow_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(WorkflowTrace).where(WorkflowTrace.id == workflow_id)
    )
    trace = result.scalar_one_or_none()

    if not trace:
        raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

    return trace


@router.get("/", summary="List recent workflows")
async def list_workflows(
    limit: int = 10,
    session_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(WorkflowTrace).order_by(WorkflowTrace.created_at.desc()).limit(limit)
    if session_id:
        query = query.where(WorkflowTrace.session_id == session_id)

    result = await db.execute(query)
    traces = result.scalars().all()

    return {
        "workflows": [
            {
                "workflow_id": str(t.id),
                "user_request": t.user_request[:100],
                "status": t.status,
                "agents_used": t.agents_used,
                "duration_ms": t.duration_ms,
                "created_at": t.created_at.isoformat(),
            }
            for t in traces
        ],
        "total": len(traces),
    }
