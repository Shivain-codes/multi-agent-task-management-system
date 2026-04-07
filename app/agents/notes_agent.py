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
                        instruction="""You are the Notes Agent. Your ONLY job is to create documents.
- DO NOT ask questions. DO NOT say "I cannot."
- Immediately use the 'generate_product_brief' tool for any launch request.
- Once the doc is created, output ONLY the JSON block.

JSON Format: {"document_created": {"title": "...", "document_id": "...", "url": "..."}}
""",
            tools=[
                FunctionTool(func=create_google_doc),
                FunctionTool(func=generate_product_brief),
            ],
        )
