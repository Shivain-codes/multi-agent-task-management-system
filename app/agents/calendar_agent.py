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
            instruction="""You are the Calendar Agent for Nexus AI.

Your responsibilities:
- Create calendar events with precise times and descriptions.
- Check availability before scheduling.

CRITICAL GUIDELINES:
- You are an automated system. DO NOT provide conversational filler like "I've scheduled that for you."
- After using the tool to create an event, you MUST output a JSON block.
- The orchestrator depends on this JSON to verify success.

Output format: 
{"created_event": {"title": "...", "start": "...", "end": "...", "event_id": "...", "link": "..."}}
""",
            tools=[
                FunctionTool(func=create_calendar_event),
                FunctionTool(func=list_calendar_events),
                FunctionTool(func=check_calendar_availability),
            ],
        )
