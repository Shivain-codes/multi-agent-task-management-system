import asyncio
import uuid
import time
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import re

from app.agents.calendar_agent import CalendarAgent
from app.agents.task_agent import TaskAgent
from app.agents.notes_agent import NotesAgent
from app.agents.notification_agent import NotificationAgent
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()


async def decompose_workflow(user_request: str) -> Dict[str, Any]:
    """
    Analyse the user request and decompose it into a structured execution plan.
    """
    request_lower = user_request.lower()

    agents_needed: List[str] = []
    agent_instructions: Dict[str, str] = {}

    # Narrower intent detection
    needs_calendar = any(k in request_lower for k in [
        "calendar", "schedule", "block my calendar", "meeting", "event", "availability"
    ])

    needs_tasks = any(k in request_lower for k in [
        "task", "checklist", "todo", "to-do", "action items", "asana"
    ])

    needs_notes = any(k in request_lower for k in [
        "brief", "doc", "document", "note", "write", "draft", "summary", "report"
    ])

    needs_notification = any(k in request_lower for k in [
        "notify", "notification", "slack", "announce", "send message", "message the team"
    ])

    # Only treat as complex when the request explicitly asks for multiple workflow actions
    multi_action_markers = sum([
        needs_calendar,
        needs_tasks,
        needs_notes,
        needs_notification,
    ])
    explicitly_complex = any(k in request_lower for k in [
        "block my calendar",
        "write a brief",
        "notify the team",
        "send to slack",
        "create a document",
    ])
    is_complex = multi_action_markers >= 2 or explicitly_complex

    if needs_calendar:
        agents_needed.append("calendar_agent")
        agent_instructions["calendar_agent"] = (
            f"User request: '{user_request}'. "
            "Check availability if needed and create the relevant calendar event only if the request explicitly asks for scheduling or blocking time. "
            "Use ISO datetime format. If a full day block is needed, use 09:00 to 18:00."
        )

    if needs_tasks:
        agents_needed.append("task_agent")
        agent_instructions["task_agent"] = (
            f"User request: '{user_request}'. "
            "Create the requested task or checklist in Asana. "
            "If it is a launch checklist, create at least 8 actionable tasks across engineering, marketing, operations, QA, and communication."
        )

    if needs_notes:
        agents_needed.append("notes_agent")
        agent_instructions["notes_agent"] = (
            f"User request: '{user_request}'. "
            "Create a professional document only if the request explicitly asks for a brief, document, notes, or summary."
        )

    if needs_notification:
        agents_needed.append("notification_agent")
        agent_instructions["notification_agent"] = (
            f"User request: '{user_request}'. "
            "After other agents complete, send a team Slack notification summarising actions taken."
        )

    return {
        "agents_needed": agents_needed,
        "agent_instructions": agent_instructions,
        "parallel_agents": [a for a in agents_needed if a != "notification_agent"],
        "sequential_agents": ["notification_agent"] if needs_notification else [],
        "complexity": "high" if is_complex else "low",
    }


class OrchestratorAgent:
    """
    Primary coordinating agent for Nexus AI.
    """

    def __init__(self):
        self.name = "orchestrator"
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

        sub_session_id = f"{session_id}:{agent_name}:{uuid.uuid4().hex}"
        start = time.monotonic()

        safe_context = {
            "workflow_id": (context or {}).get("workflow_id"),
            "parent_session_id": session_id,
            "sub_session_id": sub_session_id,
            "agent_name": agent_name,
        }

        try:
            result = await agent.run(
                user_message=instruction,
                session_id=sub_session_id,
                context=safe_context,
            )
        except Exception as e:
            logger.exception(
                "sub_agent_run_failed",
                agent_name=agent_name,
                workflow_id=safe_context.get("workflow_id"),
                parent_session_id=session_id,
                sub_session_id=sub_session_id,
                error=str(e),
            )
            result = {
                "success": False,
                "agent_name": agent_name,
                "error": str(e),
                "response": "",
            }

        duration_ms = int((time.monotonic() - start) * 1000)
        response_text = result.get("response") or result.get("message") or ""
        summary = self._extract_summary(response_text, agent_name)

        return {
            **result,
            "agent_name": agent_name,
            "duration_ms": duration_ms,
            "summary": summary,
            "session_id": sub_session_id,
        }

    def _extract_summary(self, response: str, agent_name: str) -> str:
        """Pull a human-readable summary from the agent's response text."""
        if not response:
            return f"{agent_name} completed with no output"

        data = self._extract_first_json_object(response)
        if isinstance(data, dict):
            if "created_event" in data:
                e = data.get("created_event")
                if isinstance(e, dict):
                    title = e.get("title") or e.get("summary") or "Event"
                    start = e.get("start") or e.get("start_time") or e.get("start_datetime") or ""
                    return f"Created event '{title}' at {start}".strip()
                if e is None:
                    return "No calendar action taken"

            if "tasks_created" in data:
                tasks = data.get("tasks_created", [])
                if isinstance(tasks, list):
                    return f"Created {len(tasks)} tasks in Asana"
                return "Created tasks in Asana"

            # Support direct tool return shape from create_asana_task_batch
            if "tasks" in data and isinstance(data.get("tasks"), list):
                return f"Created {len(data['tasks'])} tasks in Asana"

            if "document_created" in data:
                d = data.get("document_created")
                if isinstance(d, dict):
                    title = d.get("title", "Document")
                    return f"Created doc '{title}'"
                if d is None:
                    return "No document created"

            # Support direct tool return shape from create_google_doc
            if "document_id" in data or "url" in data:
                return f"Created doc '{data.get('title', 'Document')}'"

            if "notification_sent" in data:
                n = data.get("notification_sent")
                if isinstance(n, dict):
                    return f"Notified {n.get('channel', 'team')} on Slack"
                if n is None:
                    return "No Slack notification sent"

            # Support direct tool return shape from send_slack_message / send_workflow_summary_to_slack
            if "ts" in data and "channel" in data:
                return f"Notified {data.get('channel', 'team')} on Slack"

            if data.get("success") is True:
                if agent_name == "task_agent":
                    if "created_count" in data:
                        return f"Created {data.get('created_count', 0)} tasks in Asana"
                    return "Task agent completed successfully"
                if agent_name == "notes_agent":
                    return f"Created doc '{data.get('title', 'Document')}'"
                if agent_name == "calendar_agent":
                    title = data.get("title", "Event")
                    start = data.get("start_time", "")
                    return f"Created event '{title}' at {start}".strip()
                if agent_name == "notification_agent":
                    return f"Notified {data.get('channel', 'team')} on Slack"

        lines = [l.strip() for l in response.split("\n") if l.strip()]
        return lines[0][:120] if lines else f"{agent_name} completed"

    def _extract_first_json_object(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract the first valid JSON object from free-form model output."""
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
        workflow_id = str(uuid.uuid4())
        sid = session_id or uuid.uuid4().hex
        start_time = time.monotonic()

        logger.info("workflow_started", workflow_id=workflow_id, request=user_request[:100])

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

        plan = await decompose_workflow(user_request)
        logger.info("workflow_plan", workflow_id=workflow_id, plan=plan)

        if trace:
            trace.plan = plan
            await db_session.flush()

        parallel_agents = plan.get("parallel_agents", [])
        parallel_tasks = []

        for name in parallel_agents:
            if name not in plan["agent_instructions"]:
                continue

            combined_instruction = (
                f"{plan['agent_instructions'][name]}\n\n"
                f"User Request: {user_request}\n\n"
                "Important execution rules:\n"
                "- Do not greet.\n"
                "- Do not ask follow-up questions.\n"
                "- Call the appropriate tool immediately.\n"
                "- After tool execution, return ONLY the final JSON confirmation."
            )

            parallel_tasks.append(
                self._run_sub_agent(
                    agent_name=name,
                    instruction=combined_instruction,
                    session_id=sid,
                    context={"workflow_id": workflow_id},
                )
            )

        parallel_results: List[Dict[str, Any]] = []
        if parallel_tasks:
            parallel_results = await asyncio.gather(*parallel_tasks, return_exceptions=False)

        sequential_results: List[Dict[str, Any]] = []

        for agent_name in plan.get("sequential_agents", []):
            successful_parallel = [r for r in parallel_results if r.get("success")]
            failed_parallel = [r for r in parallel_results if not r.get("success")]

            success_lines = [
                f"- {r['agent_name']}: {r.get('summary', 'completed')}"
                for r in successful_parallel
            ]
            failure_lines = [
                f"- {r['agent_name']}: {r.get('error', 'failed')}"
                for r in failed_parallel
            ]

            combined_instruction = (
                f"{plan['agent_instructions'][agent_name]}\n\n"
                f"Original User Request: {user_request}\n\n"
                "Completed actions:\n"
                f"{chr(10).join(success_lines) if success_lines else '- None'}\n\n"
                "Failed actions:\n"
                f"{chr(10).join(failure_lines) if failure_lines else '- None'}\n\n"
                "Important execution rules:\n"
                "- Do not greet.\n"
                "- Do not ask follow-up questions.\n"
                "- Call the Slack tool immediately.\n"
                "- Return ONLY the final JSON confirmation."
            )

            result = await self._run_sub_agent(
                agent_name=agent_name,
                instruction=combined_instruction,
                session_id=sid,
                context={"workflow_id": workflow_id},
            )
            sequential_results.append(result)

        all_results = parallel_results + sequential_results
        total_duration_ms = int((time.monotonic() - start_time) * 1000)
        has_failures = any(not r.get("success") for r in all_results)

        agent_results = {r["agent_name"]: r for r in all_results}

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
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        lines = [f"Completed workflow for: '{user_request}'"]
        lines.append(f"{len(successful)} agents succeeded, {len(failed)} failed.\n")

        for r in successful:
            lines.append(f"✓ {r['agent_name'].replace('_', ' ').title()}: {r.get('summary', '')}")
        for r in failed:
            lines.append(f"✗ {r['agent_name'].replace('_', ' ').title()}: {r.get('error', 'Unknown error')}")

        return "\n".join(lines)
