from datetime import datetime

import pytz

from app.models.booking import Booking
from app.repositories.clinic_repo import ClinicRepository
from app.services.calendar_service import build_calendar_event


def test_build_calendar_event_payload() -> None:
    clinic = ClinicRepository().get("smilecare_dental")
    tz = pytz.timezone(clinic.timezone)
    booking = Booking.from_confirmed_slots(
        clinic_id=clinic.clinic_id,
        call_id="call_123",
        caller_number="+911234567890",
        patient_name="Asha Patel",
        service="Root Canal",
        start_time=tz.localize(datetime(2026, 7, 3, 15, 0)),
        duration_minutes=90,
    )

    payload = build_calendar_event(clinic, booking)

    assert payload["summary"] == "Root Canal - Asha Patel"
    assert payload["start"]["timeZone"] == "Asia/Kolkata"
    assert payload["end"]["dateTime"].endswith("+05:30")
    assert "call_123" in payload["description"]

