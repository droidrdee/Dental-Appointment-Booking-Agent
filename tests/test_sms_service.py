from datetime import datetime

import pytz

from app.models.booking import Booking
from app.repositories.clinic_repo import ClinicRepository
from app.services.sms_service import build_confirmation_message


def test_build_confirmation_message() -> None:
    clinic = ClinicRepository().get("smilecare_dental")
    tz = pytz.timezone(clinic.timezone)
    booking = Booking.from_confirmed_slots(
        clinic_id=clinic.clinic_id,
        call_id="call_123",
        caller_number="+911234567890",
        patient_name="Asha Patel",
        service="Dental Cleaning",
        start_time=tz.localize(datetime(2026, 7, 3, 15, 0)),
        duration_minutes=45,
    )

    message = build_confirmation_message(clinic, booking)

    assert "Asha Patel" in message
    assert "Dental Cleaning" in message
    assert "SmileCare Dental" in message
    assert "03:00 PM" in message

