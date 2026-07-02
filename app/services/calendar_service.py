import base64
import json
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build

from app.config import Settings, get_settings
from app.models.booking import Booking
from app.models.clinic import ClinicConfig

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]


class CalendarService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def create_event(self, clinic: ClinicConfig, booking: Booking) -> str:
        event_body = build_calendar_event(clinic, booking)
        service = get_calendar_client()
        calendar_id = self.settings.google_calendar_id or clinic.google_calendar_id
        event = (
            service.events()
            .insert(calendarId=calendar_id, body=event_body)
            .execute()
        )
        return str(event["id"])


def build_calendar_event(clinic: ClinicConfig, booking: Booking) -> dict[str, Any]:
    return {
        "summary": f"{booking.service} - {booking.patient_name}",
        "description": (
            f"Booked by Dental Appointment Booking Agent\n"
            f"Clinic: {clinic.name}\n"
            f"Call ID: {booking.call_id}\n"
            f"Caller: {booking.caller_number or 'unknown'}"
        ),
        "start": {
            "dateTime": booking.start_time.isoformat(),
            "timeZone": clinic.timezone,
        },
        "end": {
            "dateTime": booking.end_time.isoformat(),
            "timeZone": clinic.timezone,
        },
    }


def get_calendar_client():
    settings = get_settings()
    credentials = _load_credentials(settings)
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def _load_credentials(settings: Settings):
    if settings.google_service_account_json_base64:
        try:
            raw_json = base64.b64decode(
                settings.google_service_account_json_base64.encode("utf-8")
            ).decode("utf-8")
            data = json.loads(raw_json)
            return service_account.Credentials.from_service_account_info(
                data,
                scopes=CALENDAR_SCOPES,
            )
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
            try:
                data = json.loads(settings.google_service_account_json_base64)
                return service_account.Credentials.from_service_account_info(
                    data,
                    scopes=CALENDAR_SCOPES,
                )
            except json.JSONDecodeError:
                pass

    if settings.google_application_credentials:
        return service_account.Credentials.from_service_account_file(
            settings.google_application_credentials,
            scopes=CALENDAR_SCOPES,
        )

    raise RuntimeError(
        "Google Calendar credentials are not configured. Set "
        "GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SERVICE_ACCOUNT_JSON_BASE64."
    )
