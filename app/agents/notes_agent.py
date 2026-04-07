from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.agents.base_agent import BaseAgent
from app.tools.notes_tool import create_google_doc, generate_product_brief_from_request
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
            instruction="""
You are the Notes Agent.

Rules:
1. DO NOT greet the user.
2. DO NOT ask clarifying questions.
3. DO NOT explain your reasoning.
4. Create the requested document immediately using tools.
5. Prefer generate_product_brief_from_request when the request is about a launch, release, project, or plan.
6. Use create_google_doc only when you already have the final content ready.
7. After all tool calls are complete, output ONLY a valid JSON object.

Document rule:
- For product launch or release requests, generate a professional team brief with:
  - objective
  - scope
  - milestones
  - owners or teams
  - risks
  - communication plan

Output format:
{
  "document_created": {
    "title": "...",
    "document_id": "...",
    "status": "created"
  }
}

If no document is created, return:
{
  "document_created": null,
  "status": "no_action"
}
""",
            tools=[
                FunctionTool(func=create_google_doc),
                FunctionTool(func=generate_product_brief_from_request),
            ],
        )
