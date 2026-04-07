from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.agents.base_agent import BaseAgent
from app.tools.notes_tool import create_google_doc, generate_product_brief
from app.core.config import get_settings

settings = get_settings()


class NotesAgent(BaseAgent):
    """
    Sub-agent responsible for document creation and knowledge management.
    Generates Google Docs, briefs, and summaries; stores content with embeddings.
    """

    def __init__(self):
        super().__init__(
            name="notes_agent",
            description="Creates and manages documents: briefs, summaries, meeting notes",
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
                FunctionTool(func=create_google_doc),
                FunctionTool(func=generate_product_brief),
            ],
        )
