from datetime import datetime
from typing import Optional, List, Dict, Any
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import json, os
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)
settings = get_settings()

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _get_calendar_service():
    """Build and return an authenticated Google Calendar service."""
    creds = None
    token_path = "credentials/google_token.json"
    creds_path = settings.google_calendar_credentials_path

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        os.makedirs("credentials", exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


async def create_calendar_event(
    title: str,
    start_time: str,
    end_time: str,
    description: Optional[str] = None,
    attendees: Optional[List[str]] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a Google Calendar event.

    Args:
        title: Event title
        start_time: ISO format datetime string e.g. '2025-04-08T09:00:00'
        end_time: ISO format datetime string e.g. '2025-04-08T18:00:00'
        description: Optional event description
        attendees: Optional list of attendee email addresses
        location: Optional location string

    Returns:
        dict with event_id, html_link, and status
    """
    try:
        service = _get_calendar_service()

        event_body = {
            "summary": title,
            "start": {"dateTime": start_time, "timeZone": "UTC"},
            "end": {"dateTime": end_time, "timeZone": "UTC"},
        }
        if description:
            event_body["description"] = description
        if location:
            event_body["location"] = location
        if attendees:
            event_body["attendees"] = [{"email": e} for e in attendees]

        event = service.events().insert(calendarId="primary", body=event_body).execute()

        logger.info("calendar_event_created", event_id=event["id"], title=title)
        return {
            "success": True,
            "event_id": event["id"],
            "html_link": event.get("htmlLink", ""),
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
        }
    except Exception as e:
        logger.error("calendar_event_creation_failed", error=str(e))
        return {"success": False, "error": str(e)}


async def list_calendar_events(
    time_min: str,
    time_max: str,
    max_results: int = 10,
) -> Dict[str, Any]:
    """
    List upcoming calendar events in a time range.

    Args:
        time_min: ISO datetime string for range start
        time_max: ISO datetime string for range end
        max_results: Maximum number of events to return

    Returns:
        dict with list of events
    """
    try:
        service = _get_calendar_service()
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
        return {
            "success": True,
            "events": [
                {
                    "id": e["id"],
                    "title": e.get("summary", "No title"),
                    "start": e["start"].get("dateTime", e["start"].get("date")),
                    "end": e["end"].get("dateTime", e["end"].get("date")),
                    "location": e.get("location"),
                    "description": e.get("description"),
                }
                for e in events
            ],
            "total": len(events),
        }
    except Exception as e:
        logger.error("calendar_list_failed", error=str(e))
        return {"success": False, "error": str(e), "events": []}


async def check_calendar_availability(
    start_time: str,
    end_time: str,
) -> Dict[str, Any]:
    """
    Check if a time slot is available in the user's calendar.

    Args:
        start_time: ISO datetime string
        end_time: ISO datetime string

    Returns:
        dict with is_available boolean and conflicting events if any
    """
    result = await list_calendar_events(start_time, end_time, max_results=5)
    if not result["success"]:
        return result

    conflicts = result["events"]
    return {
        "success": True,
        "is_available": len(conflicts) == 0,
        "conflicts": conflicts,
    }
