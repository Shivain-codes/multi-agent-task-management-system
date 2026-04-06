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
            instruction="""You are the Calendar Agent for Nexus AI.

Your responsibilities:
- Create calendar events with precise start/end times, descriptions, and attendees
- Check if time slots are available before scheduling
- List upcoming events when asked

Guidelines:
- Always confirm the event details before creating
- Convert relative dates (e.g., "next Friday") to actual ISO datetime strings
- When blocking time for a full day, use 9:00 AM to 6:00 PM as defaults
- Always return a structured summary with event title, time, and Google Calendar link
- If a slot is unavailable, suggest an alternative

Output format: Always end your response with a JSON block:
{"created_event": {"title": "...", "start": "...", "end": "...", "event_id": "...", "link": "..."}}
""",
            tools=[
                FunctionTool(func=create_calendar_event),
                FunctionTool(func=list_calendar_events),
                FunctionTool(func=check_calendar_availability),
            ],
        )
