from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from app.agents.base_agent import BaseAgent
from app.tools.calendar_tool import (
    create_calendar_event,
    list_calendar_events,
    check_calendar_availability,
)
from app.core.config import get_settings

settings = get_settings()


class CalendarAgent(BaseAgent):
    """
    Sub-agent responsible for all Google Calendar operations.
    Can create events, check availability, and list upcoming schedule.
    """

    def __init__(self):
        super().__init__(
            name="calendar_agent",
            description="Manages Google Calendar: creates events, checks availability, lists schedule",
        )

    def _build_agent(self) -> LlmAgent:
        return LlmAgent(
            name=self.name,
            model=settings.agent_model,
            description=self.description,
            instruction="""
You are the Calendar Agent.

Rules:
1. DO NOT greet the user.
2. DO NOT ask clarifying questions.
3. DO NOT explain your reasoning.
4. Perform the task using tools immediately.
5. Use the minimum number of tool calls needed.
6. After all tool calls are complete, output ONLY a valid JSON object.

Tool usage:
- Use check_calendar_availability when availability must be verified.
- Use create_calendar_event when an event or time block should be created.
- Use list_calendar_events only if explicitly useful for the request.

Output format:
{
  "created_event": {
    "title": "...",
    "start": "...",
    "end": "...",
    "status": "created"
  }
}

If no event is created, return:
{
  "created_event": null,
  "status": "no_action"
}
""",
            tools=[
                FunctionTool(func=create_calendar_event),
                FunctionTool(func=list_calendar_events),
                FunctionTool(func=check_calendar_availability),
            ],
        )
