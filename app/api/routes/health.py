from fastapi import APIRouter
from app.api.schemas import HealthResponse
from app.db.database import check_db_health
from app.core.config import get_settings

router = APIRouter(tags=["System"])
settings = get_settings()


@router.get("/", summary="Root — system info")
async def root():
    return {
        "name": "Nexus AI",
        "description": "Multi-agent AI system for tasks, schedules, and information management",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "run_workflow": "POST /api/v1/workflows/run",
            "workflow_trace": "GET /api/v1/workflows/{id}/trace",
            "tasks": "/api/v1/tasks",
            "semantic_search": "POST /api/v1/tasks/search/semantic",
            "health": "GET /health",
        },
    }


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health():
    """
    Returns system health including database connectivity.
    Used by Cloud Run for liveness and readiness probes.
    """
    db_ok = await check_db_health()
    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        database=db_ok,
        environment=settings.app_env,
    )
