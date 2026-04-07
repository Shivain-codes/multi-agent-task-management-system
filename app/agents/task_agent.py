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
4. Perform the task immediately using Asana tools.
5. If the request contains 'checklist', 'launch checklist', 'todo', or 'multiple tasks',
   call create_asana_task_batch with EXACTLY 8 task objects for a product launch checklist.
6. Never call create_asana_task_batch with an empty list.
7. If the request is for only one task, call create_asana_task.
8. After using the tool, output ONLY valid JSON.

For a product launch checklist, create these 8 tasks:
- Finalize launch plan
- Confirm feature readiness
- Run QA and bug bash
- Prepare launch assets
- Review analytics and tracking
- Brief support team
- Schedule launch-day monitoring
- Publish launch announcement

Each task object for create_asana_task_batch must use:
- title
- description
- priority
- due_date

Output format:
{
  "tasks_created": [
    {"title": "...", "priority": "...", "due_date": "..."}
  ],
  "status": "created"
}

If nothing was created:
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
