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
            instruction="""You are the Task Agent. 
CRITICAL: You MUST use the 'create_asana_task_batch' tool immediately.
- For a 'product launch checklist', create at least 5 detailed tasks.
- Do not ask for confirmation. 
- After calling the tool, return ONLY this JSON:
{"tasks_created": [{"title": "...", "priority": "...", "due_date": "...", "gid": "..."}]} 
""",
            tools=[
                FunctionTool(func=create_asana_task),
                FunctionTool(func=create_asana_task_batch),
                FunctionTool(func=list_asana_tasks),
            ],
        )
