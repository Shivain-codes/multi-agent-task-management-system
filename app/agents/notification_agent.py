from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.agents.base_agent import BaseAgent
from app.tools.slack_tool import send_slack_message, send_workflow_summary_to_slack
from app.core.config import get_settings

settings = get_settings()


class NotificationAgent(BaseAgent):
    """
    Sub-agent responsible for team notifications via Slack.
    Sends rich Block Kit messages summarising completed workflows.
    """

    def __init__(self):
        super().__init__(
            name="notification_agent",
            description="Sends team notifications on Slack with rich workflow summaries",
        )

    def _build_agent(self) -> LlmAgent:
        return LlmAgent(
            name=self.name,
            model=settings.agent_model,
            description=self.description,
            instruction="""You are the Notification Agent for Nexus AI.

Your responsibilities:
- Send clear, professional Slack notifications to the team
- Summarise completed workflow actions in a concise, scannable format
- Format messages for human readability — not raw JSON dumps

Guidelines:
- Lead with what was accomplished, not the technical details
- Use bullet points for lists of tasks or events
- Include links to relevant Asana tasks, Google Calendar events, and Docs
- Keep the message under 500 words — teams don't read walls of text
- End with a clear call-to-action if one is needed (e.g., "Review the brief and comment by EOD")

For a product launch workflow notification:
- Announce what was set up (calendar block, task checklist, brief)
- Link to each created resource
- State the launch date prominently

Tone: Professional, helpful, and clear. Not robotic.

Output format: Always end with a JSON block:
{"notification_sent": {"channel": "...", "ts": "...", "message_preview": "..."}}
""",
            tools=[
                FunctionTool(func=send_slack_message),
                FunctionTool(func=send_workflow_summary_to_slack),
            ],
        )
