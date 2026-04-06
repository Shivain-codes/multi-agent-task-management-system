# Nexus AI — Multi-Agent AI System

> **Google Gen AI Academy Hackathon submission**
> Built on Google ADK · Gemini 1.5 Flash · AlloyDB · Cloud Run

---

## Architecture

```
User Request (natural language)
        │
        ▼
┌──────────────────────────────────────┐
│         FastAPI Gateway              │
│   Auth · Rate limiting · Sessions    │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│      Orchestrator Agent (ADK)        │
│  Decomposes request → Execution DAG  │
└──────┬──────────┬──────────┬─────────┘
       │ parallel │          │ sequential
  ┌────▼───┐ ┌────▼───┐ ┌────▼───┐ ┌──────────────┐
  │Calendar│ │  Task  │ │ Notes  │ │ Notification │
  │ Agent  │ │ Agent  │ │ Agent  │ │    Agent     │
  └────┬───┘ └────┬───┘ └────┬───┘ └──────┬───────┘
       │          │          │             │
  Google Cal   Asana MCP  Google Docs   Slack MCP
       │          │          │             │
       └──────────┴──────────┴─────────────┘
                             │
                    AlloyDB (PostgreSQL + pgvector)
                    tasks · schedules · notes · traces
```

## Demo Scenario

```bash
curl -X POST https://nexus-ai-xxxx.run.app/api/v1/workflows/run \
  -H "Content-Type: application/json" \
  -d '{
    "request": "I have a product launch next Friday. Block my calendar for the day, create a full launch checklist, write a team brief, and notify the team on Slack."
  }'
```

**What fires in under 8 seconds:**
1. Orchestrator decomposes into 4 sub-tasks
2. **Calendar Agent** → checks availability → creates all-day block in Google Calendar
3. **Task Agent** → generates 8+ actionable tasks → creates them in Asana
4. **Notes Agent** → writes a product launch brief → saves to Google Docs
5. *(Steps 2–4 run in parallel via asyncio.gather)*
6. **Notification Agent** → sends rich Block Kit summary to Slack with links
7. All data stored in AlloyDB with vector embeddings for semantic search
8. Full execution trace queryable at `/api/v1/workflows/{id}/trace`

---

## Setup

### Prerequisites
- Python 3.12+
- AlloyDB instance (reuse from mini project, region: us-central1)
- Google Cloud project with Calendar, Docs, Drive APIs enabled
- Asana account with a project
- Slack workspace with a bot token

### Local development

```bash
# 1. Clone and install
git clone https://github.com/Shivain-codes/nexus-ai
cd nexus-ai
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your keys

# 3. Initialise AlloyDB schema
psql -h $DB_HOST -U nexus_user -d nexus_db -f scripts/setup.sql

# 4. Run
uvicorn app.main:app --reload --port 8080
# API docs: http://localhost:8080/docs
```

### Deploy to Cloud Run

```bash
# Store secrets in Secret Manager first
gcloud secrets create nexus-gemini-key --data-file=- <<< "your_gemini_key"
gcloud secrets create nexus-db-password --data-file=- <<< "your_db_password"
gcloud secrets create nexus-asana-token --data-file=- <<< "your_asana_token"
gcloud secrets create nexus-slack-token --data-file=- <<< "your_slack_token"
gcloud secrets create nexus-google-client-id --data-file=- <<< "your_oauth_client_id"
gcloud secrets create nexus-google-client-secret --data-file=- <<< "your_oauth_secret"

# Deploy
chmod +x scripts/deploy.sh && ./scripts/deploy.sh
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/workflows/run` | Execute a multi-agent workflow |
| `GET`  | `/api/v1/workflows/{id}/trace` | Full execution trace |
| `GET`  | `/api/v1/workflows/` | List recent workflows |
| `POST` | `/api/v1/tasks/` | Create a task |
| `GET`  | `/api/v1/tasks/` | List tasks |
| `POST` | `/api/v1/tasks/search/semantic` | Semantic search via pgvector |
| `GET`  | `/health` | Health check |
| `GET`  | `/docs` | Interactive Swagger UI |

---

## Key Technical Decisions

| Decision | Reasoning |
|----------|-----------|
| **Google ADK v1.2.1** | Native Gemini integration, MCP toolset support, async runner |
| **AlloyDB + pgvector** | Google's managed Postgres, vector embeddings for semantic search, IVFFlat indexes |
| **asyncio.gather for parallel agents** | Calendar, Task, Notes agents run concurrently — reduces total latency ~3× |
| **InMemorySessionService per request** | Avoids `await create_session()` conflict in ADK; fresh service per call is correct pattern |
| **Workflow trace table** | Every execution stored with full plan + per-step results — fully observable |
| **Pydantic v2 schemas** | Strict validation, auto-generated OpenAPI docs |
| **Cloud Run** | Scales to zero, VPC connector reuse, managed SSL, Secret Manager integration |

---

## Project Structure

```
nexus/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py      # Primary coordinator — DAG execution engine
│   │   ├── base_agent.py        # ADK session + runner abstraction
│   │   ├── calendar_agent.py    # Google Calendar sub-agent
│   │   ├── task_agent.py        # Asana sub-agent
│   │   ├── notes_agent.py       # Google Docs sub-agent
│   │   └── notification_agent.py # Slack sub-agent
│   ├── api/
│   │   ├── schemas.py           # Pydantic request/response models
│   │   └── routes/
│   │       ├── workflows.py     # POST /run, GET /trace
│   │       ├── tasks.py         # CRUD + semantic search
│   │       └── health.py        # GET /health
│   ├── core/
│   │   ├── config.py            # Pydantic settings
│   │   └── logging.py           # Structured logging (structlog)
│   ├── db/
│   │   ├── database.py          # AsyncSession factory, init_db
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   └── vector_repo.py       # pgvector semantic search
│   ├── tools/
│   │   ├── calendar_tool.py     # Google Calendar API
│   │   ├── asana_tool.py        # Asana API
│   │   ├── slack_tool.py        # Slack SDK
│   │   ├── notes_tool.py        # Google Docs API
│   │   └── embedding_tool.py    # Gemini embeddings
│   └── main.py                  # FastAPI app factory
├── scripts/
│   ├── setup.sql                # AlloyDB schema + pgvector + IVFFlat indexes
│   └── deploy.sh                # Cloud Run build + deploy
├── Dockerfile
├── requirements.txt
└── .env.example
```

---

*Built by Shivain for Google Gen AI Academy Hackathon*
