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
            instruction="""You are the Notification Agent. 
- You will receive a list of completed actions. 
- Immediately call 'send_workflow_summary_to_slack' to update the team.
- DO NOT provide conversational filler. 
- Output ONLY the JSON block after sending.

JSON Format: {"notification_sent": {"channel": "...", "ts": "...", "message_preview": "..."}}
""",
            tools=[
                FunctionTool(func=send_slack_message),
                FunctionTool(func=send_workflow_summary_to_slack),
            ],
        )
