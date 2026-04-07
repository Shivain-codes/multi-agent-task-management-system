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
            instruction="""
You are the Task Agent.

Rules:
1. DO NOT greet the user.
2. DO NOT ask clarifying questions.
3. DO NOT explain your reasoning.
4. Create the requested tasks immediately using tools.
5. Prefer create_asana_task_batch for checklists or multiple tasks.
6. Use create_asana_task only for a single task.
7. After all tool calls are complete, output ONLY a valid JSON object.

Checklist rule:
- If the request is for a launch, release, or checklist, create at least 8 actionable tasks.
- Include a mix of engineering, marketing, operations, QA, and communication tasks where relevant.

Output format:
{
  "tasks_created": [
    {"name": "...", "priority": "...", "due_date": "..."},
    {"name": "...", "priority": "...", "due_date": "..."}
  ],
  "status": "created"
}

If no tasks are created, return:
{
  "tasks_created": [],
  "status": "no_action"
}
""",
            tools=[
                FunctionTool(func=create_asana_task),
                FunctionTool(func=create_asana_task_batch),
                FunctionTool(func=list_asana_tasks),
            ],
        )
