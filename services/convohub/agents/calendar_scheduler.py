# Query format expected by CalendarScheduler:
#   - To schedule a meeting: pass a JSON string with "prospect_name", "start_time", "email", and "mobile" fields
#   - Example: '{"prospect_name": "John Doe", "start_time": "2025-10-29T15:00", "email": "john@example.com", "mobile": "+1234567890"}'
#   - The scheduler will use the provided start_time (ISO format: YYYY-MM-DDTHH:MM), email address, and mobile phone number.
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from ..config import settings

import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class CalendarScheduler:
    """Google Calendar integration for availability checking and meeting scheduling."""

    def __init__(self):
        logger.debug("Initializing CalendarScheduler")
        self.calendar_id = settings.CALENDAR_ID
        self.default_duration = settings.DEFAULT_MEETING_DURATION_MINUTES
        self.timezone = settings.TIMEZONE
        creds_path = getattr(settings, "GOOGLE_CALENDAR_CREDENTIALS_FILE", "credentials.json")
        self.service = self._get_calendar_service(creds_path)

    def _get_calendar_service(self, creds_path):
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/calendar"]
        )
        return build("calendar", "v3", credentials=creds)

    def list_events(self) -> List[Dict[str, Any]]:
        logger.debug("Listing calendar events from Google Calendar")
        now = datetime.utcnow().isoformat() + "Z"
        events_result = self.service.events().list(
            calendarId=self.calendar_id,
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime"
        ).execute()
        events = events_result.get("items", [])
        return events

    def is_available(self, start: datetime, end: datetime) -> bool:
        logger.debug(f"Checking availability from {start} to {end} in Google Calendar")
        events = self.list_events()
        for evt in events:
            evt_start = datetime.fromisoformat(evt["start"].get("dateTime", evt["start"].get("date")))
            evt_end = datetime.fromisoformat(evt["end"].get("dateTime", evt["end"].get("date")))
            if not (end <= evt_start or start >= evt_end):
                return False
        return True

    def schedule_meeting(self, prospect_name: str, start: datetime, email: str = None, mobile: str = None) -> Dict[str, Any]:
        logger.debug(f"Scheduling meeting with {prospect_name} at {start} in Google Calendar")
        end = start + timedelta(minutes=self.default_duration)
        if not self.is_available(start, end):
            return {"scheduled": False, "reason": "Time slot not available"}
        event = {
            "summary": f"Meeting with {prospect_name}",
            "start": {"dateTime": start.isoformat(), "timeZone": self.timezone},
            "end": {"dateTime": end.isoformat(), "timeZone": self.timezone},
            "description": f"Mobile: {mobile}" if mobile else None,
        }
        if email:
            event["attendees"] = [{"email": email}]
        created_event = self.service.events().insert(calendarId=self.calendar_id, body=event).execute()
        logger.info(f"Scheduled meeting: {created_event}")
        return {"scheduled": True, "event": created_event}

    async def run(self, query: str) -> str:
        logger.debug(f"Running CalendarScheduler with query: {query[:50]}")
        import json
        try:
            data = json.loads(query)
            prospect = data.get("prospect_name")
            start_time_str = data.get("start_time")
            email = data.get("email")
            mobile = data.get("mobile")
            if not prospect or not start_time_str or not email or not mobile:
                return "JSON must include 'prospect_name', 'start_time', 'email', and 'mobile'."
            try:
                start_time = datetime.fromisoformat(start_time_str)
            except Exception:
                return "Invalid start_time format. Use YYYY-MM-DDTHH:MM."
            result = self.schedule_meeting(prospect, start_time, email=email, mobile=mobile)
            if result.get("scheduled"):
                evt = result["event"]
                return (
                    f"Scheduled meeting with {prospect} ({email}, {mobile}) on {evt['start']['dateTime']} for {self.default_duration} minutes."
                )
            else:
                return f"Unable to schedule meeting: {result.get('reason')}"
        except Exception:
            return "Query must be a JSON string with 'prospect_name', 'start_time', 'email', and 'mobile'."

def calendar_scheduler_tool() -> Dict[str, Any]:
    async def _invoke(input_text: str) -> str:
        logger.debug(f"Invoking CalendarScheduler with input_text: {input_text[:50]}")
        scheduler = CalendarScheduler()
        return await scheduler.run(input_text)
    return {
        "name": "calendar_scheduler",
        "description": "Checks availability and schedules meetings in Google Calendar (stub).",
        "callable": _invoke,
    }
