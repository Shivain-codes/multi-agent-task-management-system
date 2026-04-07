from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.agents.base_agent import BaseAgent
from app.tools.asana_tool import (
    create_asana_task,
    create_asana_task_batch,
    list_asana_tasks,
)
from app.core.config import get_settings

settings = get_settings()


class TaskAgent(BaseAgent):
    """
    Sub-agent responsible for task management via Asana.
    Creates individual tasks and full checklists; tracks priorities and due dates.
    """

    def __init__(self):
        super().__init__(
            name="task_agent",
            description="Manages tasks in Asana: creates tasks, builds checklists, sets priorities",
        )

    def _build_agent(self) -> LlmAgent:
        return LlmAgent(
            name=self.name,
            model=settings.agent_model,
            description=self.description,
            instruction="""You are the Task Agent for Nexus AI.

Your responsibilities:
- Create individual tasks in Asana with appropriate priority and due dates
- Build comprehensive task checklists from high-level goals
- Retrieve and summarize existing tasks

Guidelines:
- For a "product launch" request, generate at least 5 specific, actionable tasks
- CRITICAL: If the request is for a 'launch checklist', you MUST create at least 5-8 separate tasks in Asana immediately. Do not return an empty list.
- Assign realistic due dates relative to the launch date
- Always set priority: use 'high' for launch-day tasks, 'medium' for prep, 'low' for post-launch
- Task titles should be action-oriented: "Finalize press kit", not "Press kit"
- Group tasks logically by phase (Preparation, Launch Day, Post-Launch)

When generating a launch checklist, include tasks across these areas:
1. Engineering (performance testing, deployment runbook, rollback plan)
2. Marketing (blog post, social media, press release)
3. Design (final asset delivery, screenshots)
4. Customer Success (FAQ document, support training)
5. Analytics (tracking setup, dashboard creation)

Output format: Always end with a JSON block:
{"tasks_created": [{"title": "...", "priority": "...", "due_date": "...", "gid": "..."}]}
""",
            tools=[
                FunctionTool(func=create_asana_task),
                FunctionTool(func=create_asana_task_batch),
                FunctionTool(func=list_asana_tasks),
            ],
        )
