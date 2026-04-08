from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging, get_logger
from app.db.database import init_db
from app.api.routes import health, workflows, tasks

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    setup_logging()
    logger = get_logger("nexus.startup")
    logger.info("nexus_starting", env=settings.app_env, model=settings.agent_model)

    # Initialise DB tables (idempotent — safe to call on every startup)
    try:
        await init_db()
        logger.info("database_ready")
    except Exception as e:
        logger.warning("database_init_skipped", reason=str(e))

    logger.info("nexus_ready", port=settings.app_port)
    yield

    logger.info("nexus_shutting_down")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Nexus AI",
        description="""
## Multi-agent AI system for tasks, schedules, and information management

Built on **Google ADK**, **Gemini**, and **Cloud SQL** for the Google Gen AI Academy Hackathon.

### Key capabilities
- **Natural language workflow execution** — one prompt orchestrates 4 agents in parallel
- **Google Calendar integration** — schedule events, check availability
- **Asana task management** — create checklists, set priorities and due dates
- **Google Docs notes** — generate briefs and documents automatically
- **Slack notifications** — rich team updates via Block Kit
- **Semantic search** — pgvector cosine similarity across all stored data
- **Full workflow tracing** — every agent step recorded and queryable

### Demo scenario
```
POST /api/v1/workflows/run
{
  "request": "I have a product launch next Friday. Block my calendar, create a launch checklist, write a team brief, and notify the team on Slack."
}
```
        """,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router)
    app.include_router(workflows.router, prefix="/api/v1")
    app.include_router(tasks.router, prefix="/api/v1")

    return app


app = create_app()
