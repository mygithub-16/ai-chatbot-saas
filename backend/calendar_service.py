from __future__ import annotations

import os
import json
import logging
from datetime import datetime, timedelta
import dateutil.parser
from typing import Any, Dict

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger("echura.calendar")

DEFAULT_TIMEZONE = "Africa/Lagos"


def parse_booking_datetime(date_str: str, time_str: str) -> datetime:
    """
    Robustly parses date and time strings from chatbot slots into a datetime object.
    Falls back to current datetime if parsing fails.
    """
    combined = f"{date_str.strip()} {time_str.strip()}"
    try:
        return dateutil.parser.parse(combined)
    except Exception:
        try:
            d = dateutil.parser.parse(date_str)
            t = dateutil.parser.parse(time_str)
            return datetime(d.year, d.month, d.day, t.hour, t.minute, t.second)
        except Exception as e:
            logger.warning(f"Failed to parse booking datetime (date: {date_str}, time: {time_str}). Fallback to now. Error: {e}")
            return datetime.utcnow()


def create_calendar_event(
    calendar_token_json_str: str,
    calendar_id: str | None,
    slots: Dict[str, Any],
    business_name: str
) -> Dict[str, Any]:
    """
    Creates a Google Calendar event. If using mock tokens or missing Google client settings,
    simulates the event creation offline.
    """
    if not calendar_id:
        calendar_id = "primary"

    try:
        token_data = json.loads(calendar_token_json_str)
    except Exception as e:
        logger.error(f"Failed to parse calendar_token JSON: {e}")
        return {"error": "Invalid calendar token format", "mock": True, "id": f"mock-err-{int(datetime.utcnow().timestamp())}"}

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    is_mock = token_data.get("token") == "mock-access-token" or not client_id

    # 1. Parse date/time
    date_str = str(slots.get("date", ""))
    time_str = str(slots.get("time", ""))
    start_dt = parse_booking_datetime(date_str, time_str)
    # Default booking duration: 1 hour
    end_dt = start_dt + timedelta(hours=1)

    summary = f"ECHURA Booking: {slots.get('name', 'Client')}"
    description = (
        f"Business: {business_name}\n"
        f"Service: {slots.get('service', 'Consultation')}\n"
        f"Contact: {slots.get('phone', 'N/A')}\n"
        f"Captured via ECHURA AI Receptionist"
    )

    event_body = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": DEFAULT_TIMEZONE,
        },
        "end": {
            "dateTime": end_dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": DEFAULT_TIMEZONE,
        },
    }

    if is_mock:
        mock_id = f"mock-event-{int(start_dt.timestamp())}-{slots.get('name', 'client')[:4]}"
        logger.info(
            f"[MOCK GOOGLE CALENDAR] Simulated event creation:\n"
            f"  Event ID: {mock_id}\n"
            f"  Summary: {summary}\n"
            f"  Start: {event_body['start']['dateTime']} ({DEFAULT_TIMEZONE})\n"
            f"  End: {event_body['end']['dateTime']} ({DEFAULT_TIMEZONE})"
        )
        return {
            "id": mock_id,
            "status": "confirmed",
            "htmlLink": "https://calendar.google.com/calendar/r",
            "mock": True,
            "start": event_body["start"]["dateTime"],
            "end": event_body["end"]["dateTime"]
        }

    # 2. Real API interaction
    try:
        credentials = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=client_id,
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
            scopes=token_data.get("scopes", ["https://www.googleapis.com/auth/calendar"])
        )
        
        # Build service using discovery API
        service = build("calendar", "v3", credentials=credentials)
        created_event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        
        logger.info(f"Google Calendar event created successfully. Event ID: {created_event.get('id')}")
        return created_event
    except Exception as e:
        logger.exception(f"Error creating Google Calendar event: {e}")
        # Return fallback mock status so user is not blocked
        fallback_id = f"fallback-event-{int(start_dt.timestamp())}"
        return {
            "id": fallback_id,
            "error": str(e),
            "status": "failed_real_api_fallback",
            "mock": True
        }
