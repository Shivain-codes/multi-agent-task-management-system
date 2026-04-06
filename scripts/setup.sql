-- ─────────────────────────────────────────────────────────────────────────────
-- Nexus AI — AlloyDB Schema
-- Run once: psql -h <DB_HOST> -U nexus_user -d nexus_db -f scripts/setup.sql
-- ─────────────────────────────────────────────────────────────────────────────

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Enums ─────────────────────────────────────────────────────────────────────
DO $$ BEGIN
    CREATE TYPE task_status   AS ENUM ('pending','in_progress','completed','cancelled');
    CREATE TYPE task_priority AS ENUM ('low','medium','high','urgent');
    CREATE TYPE workflow_status AS ENUM ('running','completed','failed','partial');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── workflow_traces (created first — referenced by FK) ────────────────────────
CREATE TABLE IF NOT EXISTS workflow_traces (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      TEXT NOT NULL,
    user_request    TEXT NOT NULL,
    status          workflow_status NOT NULL DEFAULT 'running',
    plan            JSONB,
    steps           JSONB DEFAULT '[]',
    result          JSONB,
    error           TEXT,
    duration_ms     INTEGER,
    agents_used     JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_workflow_session   ON workflow_traces(session_id);
CREATE INDEX IF NOT EXISTS idx_workflow_status    ON workflow_traces(status);
CREATE INDEX IF NOT EXISTS idx_workflow_created   ON workflow_traces(created_at DESC);

-- ── tasks ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    status          task_status NOT NULL DEFAULT 'pending',
    priority        task_priority NOT NULL DEFAULT 'medium',
    due_date        TIMESTAMPTZ,
    tags            JSONB DEFAULT '[]',
    asana_task_gid  VARCHAR(100),
    workflow_id     UUID REFERENCES workflow_traces(id) ON DELETE SET NULL,
    embedding       VECTOR(768),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tasks_status     ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority   ON tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_workflow   ON tasks(workflow_id);
CREATE INDEX IF NOT EXISTS idx_tasks_due        ON tasks(due_date);
-- IVFFlat index for fast ANN search over embeddings
CREATE INDEX IF NOT EXISTS idx_tasks_embedding
    ON tasks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── schedules ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS schedules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(500) NOT NULL,
    description     TEXT,
    start_time      TIMESTAMPTZ NOT NULL,
    end_time        TIMESTAMPTZ NOT NULL,
    attendees       JSONB DEFAULT '[]',
    location        VARCHAR(300),
    google_event_id VARCHAR(200),
    is_all_day      BOOLEAN DEFAULT FALSE,
    workflow_id     UUID REFERENCES workflow_traces(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_schedules_time     ON schedules(start_time, end_time);
CREATE INDEX IF NOT EXISTS idx_schedules_workflow ON schedules(workflow_id);

-- ── notes ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notes (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           VARCHAR(500) NOT NULL,
    content         TEXT NOT NULL,
    tags            JSONB DEFAULT '[]',
    source          VARCHAR(100) DEFAULT 'user',
    google_doc_id   VARCHAR(200),
    workflow_id     UUID REFERENCES workflow_traces(id) ON DELETE SET NULL,
    embedding       VECTOR(768),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notes_workflow  ON notes(workflow_id);
CREATE INDEX IF NOT EXISTS idx_notes_embedding
    ON notes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ── agent_memory ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS agent_memory (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      TEXT NOT NULL,
    agent_name      VARCHAR(100) NOT NULL,
    memory_type     VARCHAR(50),
    content         TEXT NOT NULL,
    metadata        JSONB DEFAULT '{}',
    embedding       VECTOR(768),
    ttl_hours       INTEGER DEFAULT 168,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_memory_session   ON agent_memory(session_id);
CREATE INDEX IF NOT EXISTS idx_memory_agent     ON agent_memory(agent_name);
CREATE INDEX IF NOT EXISTS idx_memory_embedding
    ON agent_memory USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- ── Auto-update updated_at ────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DO $$ BEGIN
    CREATE TRIGGER tasks_updated_at     BEFORE UPDATE ON tasks     FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    CREATE TRIGGER schedules_updated_at BEFORE UPDATE ON schedules FOR EACH ROW EXECUTE FUNCTION update_updated_at();
    CREATE TRIGGER notes_updated_at     BEFORE UPDATE ON notes     FOR EACH ROW EXECUTE FUNCTION update_updated_at();
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Seed a demo workflow (optional, for testing) ──────────────────────────────
-- INSERT INTO workflow_traces (session_id, user_request, status)
-- VALUES ('demo-session-001', 'Plan a product launch for next Friday', 'completed');

SELECT 'Nexus AI schema initialised successfully.' AS status;
