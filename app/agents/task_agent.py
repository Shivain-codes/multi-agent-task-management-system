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

Guidelines:
- For "product launch" requests, generate at least 8 specific, actionable tasks.
- Group tasks by phase (Preparation, Launch Day, Post-Launch).

CRITICAL GUIDELINES:
- DO NOT ask for clarification. Execute based on the user request immediately.
- Your final response MUST be a JSON block containing the list of tasks created.
- This JSON is mandatory for the workflow trace.

Output format:
{"tasks_created": [{"title": "...", "priority": "...", "due_date": "...", "gid": "..."}]}
""",
            tools=[
                FunctionTool(func=create_asana_task),
                FunctionTool(func=create_asana_task_batch),
                FunctionTool(func=list_asana_tasks),
            ],
        )
