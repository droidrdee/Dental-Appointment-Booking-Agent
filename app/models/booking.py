from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    FAILED = "failed"


class Booking(BaseModel):
    booking_id: str = Field(default_factory=lambda: f"booking_{uuid4().hex}")
    clinic_id: str
    call_id: str
    caller_number: str | None = None
    patient_name: str
    service: str
    start_time: datetime
    end_time: datetime
    google_event_id: str | None = None
    sms_sid: str | None = None
    sms_error: str | None = None
    status: BookingStatus = BookingStatus.CONFIRMED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def from_confirmed_slots(
        cls,
        *,
        clinic_id: str,
        call_id: str,
        caller_number: str | None,
        patient_name: str,
        service: str,
        start_time: datetime,
        duration_minutes: int,
    ) -> "Booking":
        return cls(
            clinic_id=clinic_id,
            call_id=call_id,
            caller_number=caller_number,
            patient_name=patient_name,
            service=service,
            start_time=start_time,
            end_time=start_time + timedelta(minutes=duration_minutes),
        )

