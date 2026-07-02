from datetime import timedelta
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models.booking import Booking
from app.repositories.clinic_repo import ClinicRepository
from app.repositories.firestore_client import get_firestore_client
from app.services.calendar_service import CalendarService
from app.services.sms_service import SmsService


def main() -> None:
    clinic = ClinicRepository(use_firestore=False).get("smilecare_dental")
    service = clinic.services[0]
    start_time = _next_open_slot(clinic)
    booking = Booking.from_confirmed_slots(
        clinic_id=clinic.clinic_id,
        call_id="integration_verify",
        caller_number=None,
        patient_name="Integration Test",
        service=service.name,
        start_time=start_time,
        duration_minutes=service.duration_minutes,
    )

    event_id = CalendarService().create_event(clinic, booking)
    print(f"Calendar event created: {event_id}")

    sms_sid = SmsService().send_confirmation(None, clinic, booking)
    print(f"SMS sent: {sms_sid}")

    db = get_firestore_client()
    doc_ref = db.collection("integration_checks").document("latest")
    doc_ref.set({"calendar_event_id": event_id, "sms_sid": sms_sid})
    snapshot = doc_ref.get()
    print(f"Firestore write/read ok: {snapshot.exists}")


def _next_open_slot(clinic):
    import pytz
    from datetime import datetime

    timezone = pytz.timezone(clinic.timezone)
    candidate = datetime.now(timezone).replace(
        hour=11,
        minute=0,
        second=0,
        microsecond=0,
    ) + timedelta(days=1)

    while candidate.strftime("%A").lower() not in {
        "monday",
        "tuesday",
        "wednesday",
        "thursday",
        "friday",
    }:
        candidate += timedelta(days=1)
    return candidate


if __name__ == "__main__":
    main()
