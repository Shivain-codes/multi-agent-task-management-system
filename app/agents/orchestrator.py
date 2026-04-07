import asyncio
import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import re

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai.types import Content, Part

from app.agents.base_agent import APP_NAME
from app.agents.calendar_agent import CalendarAgent
from app.agents.task_agent import TaskAgent
from app.agents.notes_agent import NotesAgent
from app.agents.notification_agent import NotificationAgent
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


# ── Planner tool (called by the orchestrator LLM internally) ─────────────────

async def decompose_workflow(user_request: str) -> Dict[str, Any]:
    """
    Analyse the user request and decompose it into a structured execution plan.

    Args:
        user_request: The natural language request from the user

    Returns:
        A plan dict with agents_needed and per-agent instructions
    """
    request_lower = user_request.lower()

    agents_needed = []
    agent_instructions = {}

    # Intent detection — determines which agents fire
    needs_calendar = any(k in request_lower for k in [
        "calendar", "schedule", "block", "meeting", "event", "time", "day", "date"
    ])
    needs_tasks = any(k in request_lower for k in [
        "task", "checklist", "todo", "list", "action", "prepare", "create"
    ])
    needs_notes = any(k in request_lower for k in [
        "brief", "doc", "note", "write", "draft", "summary", "plan", "report"
    ])
    needs_notification = any(k in request_lower for k in [
        "notify", "slack", "team", "announce", "send", "message", "notify"
    ])

    # For complex requests like product launch, activate all agents
    is_complex = any(k in request_lower for k in [
        "launch", "project", "sprint", "campaign", "release", "event"
    ])
    if is_complex:
        needs_calendar = needs_tasks = needs_notes = needs_notification = True

    if needs_calendar:
        agents_needed.append("calendar_agent")
        agent_instructions["calendar_agent"] = (
            f"Based on this user request: '{user_request}' — "
            "identify the date/time mentioned, check availability, and create the appropriate calendar event(s). "
            "Use ISO datetime format. If a full day block is needed, use 9:00 AM to 6:00 PM."
        )

    if needs_tasks:
        agents_needed.append("task_agent")
        agent_instructions["task_agent"] = (
            f"Based on this user request: '{user_request}' — "
            "generate a comprehensive, actionable task checklist. "
            "Create tasks in Asana with appropriate priorities and due dates. "
            "For a launch, create at least 8 tasks across engineering, marketing, and ops."
        )

    if needs_notes:
        agents_needed.append("notes_agent")
        agent_instructions["notes_agent"] = (
            f"Based on this user request: '{user_request}' — "
            "create a professional document (brief, plan, or summary) in Google Docs. "
            "Make it comprehensive and ready to share with the team."
        )

    if needs_notification:
        agents_needed.append("notification_agent")
        agent_instructions["notification_agent"] = (
            f"After other agents complete, send a team Slack notification summarising "
            f"all actions taken for: '{user_request}'. "
            "Include links to created resources. Keep it professional and scannable."
        )

    return {
        "agents_needed": agents_needed,
        "agent_instructions": agent_instructions,
        "parallel_agents": [a for a in agents_needed if a != "notification_agent"],
        "sequential_agents": ["notification_agent"] if needs_notification else [],
        "complexity": "high" if is_complex else "medium",
    }


# ── Orchestrator ──────────────────────────────────────────────────────────────

class OrchestratorAgent:
    """
    Primary coordinating agent for Nexus AI.

    Workflow:
    1. Receives user natural language request
    2. Calls decompose_workflow() to build an execution plan
    3. Runs parallel agents (calendar, task, notes) concurrently via asyncio.gather
    4. Runs sequential agents (notification) after parallel phase completes
    5. Aggregates all results and returns a unified response
    6. Persists the full workflow trace to AlloyDB
    """

    def __init__(self):
        self.name = "orchestrator"
        # Instantiate sub-agents once — they cache their LlmAgent internally
        self._sub_agents: Dict[str, Any] = {
            "calendar_agent": CalendarAgent(),
            "task_agent": TaskAgent(),
            "notes_agent": NotesAgent(),
            "notification_agent": NotificationAgent(),
        }

    async def _run_sub_agent(
        self,
        agent_name: str,
        instruction: str,
        session_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run a single sub-agent and return its result with timing."""
        agent = self._sub_agents.get(agent_name)
        if not agent:
            return {
                "success": False,
                "agent_name": agent_name,
                "error": f"Unknown agent: {agent_name}",
                "summary": "Agent not found",
            }

        start = time.monotonic()
        result = await agent.run(
            user_message=instruction,
            session_id=session_id,
            context=context,
        )
        duration_ms = int((time.monotonic() - start) * 1000)

        # Extract JSON summary from agent response if present
        summary = self._extract_summary(result.get("response", ""), agent_name)

        return {
            **result,
            "duration_ms": duration_ms,
            "summary": summary,
        }

    def _extract_summary(self, response: str, agent_name: str) -> str:
        """Pull a human-readable summary from the agent's response text."""
        if not response:
            return f"{agent_name} completed with no output"

        data = self._extract_first_json_object(response)
        if isinstance(data, dict):
            if "created_event" in data:
                e = data.get("created_event") or {}
                if isinstance(e, dict):
                    title = e.get("title") or e.get("summary") or "Event"
                    start = e.get("start") or e.get("start_time") or e.get("start_datetime") or ""
                    return f"Created event '{title}' at {start}".strip()
                return "Created calendar event"

            if "tasks_created" in data:
                tasks = data.get("tasks_created", [])
                if isinstance(tasks, list):
                    return f"Created {len(tasks)} tasks in Asana"
                return "Created tasks in Asana"

            if "document_created" in data:
                d = data.get("document_created") or {}
                if isinstance(d, dict):
                    return f"Created doc '{d.get('title', 'Document')}'"
                return "Created document"

            if "notification_sent" in data:
                n = data.get("notification_sent") or {}
                if isinstance(n, dict):
                    return f"Notified {n.get('channel', 'team')} on Slack"
                return "Sent Slack notification"

        # Fallback: first 120 chars of response
        lines = [l.strip() for l in response.split("\n") if l.strip()]
        return lines[0][:120] if lines else f"{agent_name} completed"

    def _extract_first_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract the first valid JSON object from free-form model output."""
        # Prefer fenced JSON blocks when available.
        fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        for block in fenced_blocks:
            try:
                parsed = json.loads(block)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue

        start = text.find("{")
        while start != -1:
            depth = 0
            in_string = False
            escaped = False

            for i in range(start, len(text)):
                ch = text[i]

                if in_string:
                    if escaped:
                        escaped = False
                    elif ch == "\\":
                        escaped = True
                    elif ch == '"':
                        in_string = False
                    continue

                if ch == '"':
                    in_string = True
                    continue

                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:i + 1]
                        try:
                            parsed = json.loads(candidate)
                            if isinstance(parsed, dict):
                                return parsed
                        except json.JSONDecodeError:
                            break

            start = text.find("{", start + 1)

        return None

    async def run(
        self,
        user_request: str,
        session_id: Optional[str] = None,
        db_session=None,
    ) -> Dict[str, Any]:
        """
        Main entry point. Executes the full multi-agent workflow.

        Args:
            user_request: Natural language request from the user
            session_id: Optional session ID for continuity
            db_session: Optional AsyncSession for persisting the workflow trace

        Returns:
            Comprehensive workflow result dict
        """
        workflow_id = str(uuid.uuid4())
        sid = session_id or uuid.uuid4().hex
        start_time = time.monotonic()

        logger.info("workflow_started", workflow_id=workflow_id, request=user_request[:100])

        # ── Step 1: Persist initial trace ────────────────────────────────────
        trace = None
        if db_session:
            from app.db.models import WorkflowTrace, WorkflowStatus
            trace = WorkflowTrace(
                id=uuid.UUID(workflow_id),
                session_id=sid,
                user_request=user_request,
                status=WorkflowStatus.RUNNING,
            )
            db_session.add(trace)
            await db_session.flush()

        # ── Step 2: Decompose into plan ───────────────────────────────────────
        plan = await decompose_workflow(user_request)
        logger.info("workflow_plan", workflow_id=workflow_id, plan=plan)

        if trace:
            trace.plan = plan
            await db_session.flush()

        # ── Step 3: Run parallel agents ───────────────────────────────────────
        parallel_agents = plan.get("parallel_agents", [])
        parallel_tasks = [
            self._run_sub_agent(
                agent_name=name,
                instruction=plan["agent_instructions"][name],
                session_id=sid,
                context={"workflow_id": workflow_id, "user_request": user_request},
            )
            for name in parallel_agents
            if name in plan["agent_instructions"]
        ]

        parallel_results: List[Dict[str, Any]] = []
        if parallel_tasks:
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=False)

        # ── Step 4: Run sequential agents ───
        sequential_results: List[Dict[str, Any]] = []
        for agent_name in plan.get("sequential_agents", []):
            if agent_name not in plan["agent_instructions"]:
                continue

            # Create a clean instruction string with the data included
            parallel_summary = "\n".join(
                [f"- {r['agent_name']}: {r.get('summary')}" for r in parallel_results]
            )
            task_instruction = (
                f"The following actions were completed: {parallel_summary}. "
                "Please notify the team now."
            )

            result = await self._run_sub_agent(
                agent_name=agent_name,
                instruction=task_instruction,
                session_id=sid,
                context={"workflow_id": workflow_id},
            )
            sequential_results.append(result)

        # ── Step 5: Aggregate ─────────────────────────────────────────────────
        all_results = parallel_results + sequential_results
        total_duration_ms = int((time.monotonic() - start_time) * 1000)
        has_failures = any(not r.get("success") for r in all_results)

        agent_results = {r["agent_name"]: r for r in all_results}

        # Build step-by-step trace for the /trace endpoint
        steps = [
            {
                "step": i + 1,
                "agent": r["agent_name"],
                "success": r.get("success"),
                "duration_ms": r.get("duration_ms"),
                "summary": r.get("summary"),
                "phase": "parallel" if r["agent_name"] in parallel_agents else "sequential",
            }
            for i, r in enumerate(all_results)
        ]

        final_result = {
            "workflow_id": workflow_id,
            "session_id": sid,
            "user_request": user_request,
            "status": "partial" if has_failures else "completed",
            "plan": plan,
            "agent_results": agent_results,
            "steps": steps,
            "duration_ms": total_duration_ms,
            "agents_used": [r["agent_name"] for r in all_results],
            "summary": self._build_workflow_summary(user_request, all_results),
        }

        # ── Step 6: Update trace in DB ────────────────────────────────────────
        if trace and db_session:
            from app.db.models import WorkflowStatus
            trace.status = (
                WorkflowStatus.PARTIAL if has_failures else WorkflowStatus.COMPLETED
            )
            trace.result = {k: v for k, v in final_result.items() if k != "agent_results"}
            trace.steps = steps
            trace.duration_ms = total_duration_ms
            trace.agents_used = final_result["agents_used"]
            trace.completed_at = datetime.utcnow()
            await db_session.flush()

        logger.info(
            "workflow_completed",
            workflow_id=workflow_id,
            duration_ms=total_duration_ms,
            agents=len(all_results),
            status=final_result["status"],
        )

        return final_result

    def _build_workflow_summary(
        self, user_request: str, results: List[Dict[str, Any]]
    ) -> str:
        """Build a human-readable summary of the entire workflow."""
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        lines = [f"Completed workflow for: '{user_request}'"]
        lines.append(f"{len(successful)} agents succeeded, {len(failed)} failed.\n")

        for r in successful:
            lines.append(f"✓ {r['agent_name'].replace('_', ' ').title()}: {r.get('summary', '')}")
        for r in failed:
            lines.append(f"✗ {r['agent_name'].replace('_', ' ').title()}: {r.get('error', 'Unknown error')}")

        return "\n".join(lines)
