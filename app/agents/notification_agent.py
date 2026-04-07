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
            instruction="""
You are the Notification Agent.

Rules:
1. DO NOT greet the user.
2. DO NOT ask clarifying questions.
3. DO NOT explain your reasoning.
4. Immediately send the Slack update using the most suitable tool.
5. Prefer send_workflow_summary_to_slack when workflow_id, user_request, and summary_text are available.
6. Use send_slack_message only for a simple plain-text fallback.
7. After the tool call is complete, output ONLY a valid JSON object.

Message rule:
- Summarise completed actions clearly.
- Mention failures if any.
- Keep it concise and professional.

Output format:
{
  "notification_sent": {
    "channel": "...",
    "ts": "...",
    "message_preview": "..."
  },
  "status": "sent"
}

If no notification is sent, return:
{
  "notification_sent": null,
  "status": "no_action"
}
""",
            tools=[
                FunctionTool(func=send_slack_message),
                FunctionTool(func=send_workflow_summary_to_slack),
            ],
        )
