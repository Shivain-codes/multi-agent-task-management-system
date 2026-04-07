from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.agents.base_agent import BaseAgent
from app.tools.asana_tool import (
    create_asana_task,
    create_asana_task_batch,
    create_product_launch_checklist,
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
4. Perform the task immediately using Asana tools.
5. If the request mentions "product launch checklist", "launch checklist", or similar,
   you MUST call create_product_launch_checklist.
6. Use create_asana_task only for a true single-task request.
7. Use create_asana_task_batch only when you already have a complete non-empty tasks list.
8. After the tool call, output ONLY a valid JSON object.

Examples:
- "Create a task called product launch checklist" -> use create_product_launch_checklist
- "Create a launch checklist" -> use create_product_launch_checklist
- "Create one task called Follow up with vendor" -> use create_asana_task

Output format:
{
  "tasks_created": [
    {"title": "...", "priority": "...", "due_date": "..."}
  ],
  "status": "created"
}
""",
            tools=[
                FunctionTool(func=create_asana_task),
                FunctionTool(func=create_asana_task_batch),
                FunctionTool(func=create_product_launch_checklist),
                FunctionTool(func=list_asana_tasks),
            ],
        )
