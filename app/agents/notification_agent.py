from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.agents.base_agent import BaseAgent
from app.tools.slack_tool import send_slack_message, send_workflow_summary_to_slack
from app.core.config import get_settings

settings = get_settings()

class NotificationAgent(BaseAgent):
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

Guidelines:
- Summarize the actions taken by the Calendar, Task, and Notes agents.
- Use professional, scannable Block Kit formatting.

CRITICAL GUIDELINES:
- DO NOT say "I am ready to send." Just SEND the message using the tool.
- Once the message is sent, you MUST provide the JSON confirmation.

Output format:
{"notification_sent": {"channel": "...", "ts": "...", "message_preview": "..."}}
""",
            tools=[
                FunctionTool(func=send_slack_message),
                FunctionTool(func=send_workflow_summary_to_slack),
            ],
        )
